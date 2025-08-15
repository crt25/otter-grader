from traitlets.config import Config

import typing as t
import nbformat
from nbformat import NotebookNode
import os
from ipykernel.comm import Comm

shared_drive_dir = "/drive"
shared_drive_temp_dir = f"{shared_drive_dir}/_temp"

class JupyterLiteRunner:
    """
    A class to run JupyterLite notebooks in a JupyterLite environment.
    """

    def __init__(self, config: Config):
        self.command_prefix = "$!__jupyter_lite_extension_procedure_call"
        self.command_separator = ";"
        self.command_parameter_separator = "="
        self.command_run_notebook = "run_notebook"
        self.comm = Comm(target_name='notebook-runner')
        self.ignore_errors: bool = config.ExecutePreprocessor.allow_errors

    def execute_jupyter_command(self, command: str, **kwargs) -> None:
        """
        Sends a command to the JupyterLite environment to execute a specific action.
        """
        self.comm.send(data={'text': f"{self.command_prefix}{self.command_separator}{command}{self.command_separator}{self.command_separator.join(f'{k}{self.command_parameter_separator}{v}' for k, v in kwargs.items())}"})

    def run_notebook(self, path: str) -> None:
        """
        Runs all cells above the specified command in the JupyterLite notebook.
        """

        # remove /drive prefix from the path if it exists
        # because the paths supplied must be relative to the shared drive directory
        if path.startswith(shared_drive_dir):
            path = path[len(shared_drive_dir):]
        else:
            raise ValueError(f"Path {path} does not start with {shared_drive_dir}. Please provide a path on the shared drive directory.")
            

        self.execute_jupyter_command(self.command_run_notebook, path=path)
    
    def startExecutingNotebook(self, nb: NotebookNode) -> str:
        """
        Runs the notebook in the JupyterLite environment by sending a message to the main javascript thread.
        There must be a JupyterLite extension installed that listens for this message and executes the notebook.
        """

        # the current working directory is of the form '/tmp/tmp8nzfq2t5/autograder/submission'
        # meaning the temporary directory is two levels above the current directory
        submission_dir = os.getcwd()

        # move the temporary directory to the drive
        # this is necessary because JupyterLite only shares files in the /drive directory

        if not os.path.exists(shared_drive_dir):
            raise FileNotFoundError("The /drive directory does not exist. Please ensure you are running in a JupyterLite environment with the /drive directory available.")

         # prepend a notebook cell to the notebook that executes the python code 'print("Hello, JupyterLite!")'
        nb.cells.insert(0, nbformat.v4.new_code_cell(
            source=f"""
import micropip
import os
import time

await micropip.install("/jupyter/pypi/otter_grader-6.1.3-py3-none-any.whl")

os.chdir("{submission_dir}")

            """,
            metadata={
                "jupyter": {
                    "source_hidden": False,
                    "outputs_hidden": False,
                }
            }
        ))

        nb.cells.append(nbformat.v4.new_code_cell(
            source=f"""
import os
os.chdir("{shared_drive_dir}")
            """,
            metadata={
                "jupyter": {
                    "source_hidden": False,
                    "outputs_hidden": False,
                }
            }
        ))

        # create the shared drive temporary directory if it does not exist
        if not os.path.exists(shared_drive_temp_dir):
            os.makedirs(shared_drive_temp_dir)
        

        temp_filename = f"_temp_notebook.ipynb"
        temp_filepath = f"{shared_drive_temp_dir}/{temp_filename}"

        
        print(f"Writing notebook to {temp_filepath}")

        # remove if exists
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

        nbformat.write(nb, temp_filepath)

        print(f"Running notebook at {temp_filepath} (cwd: {submission_dir})")

        self.run_notebook(temp_filepath)

        return temp_filepath