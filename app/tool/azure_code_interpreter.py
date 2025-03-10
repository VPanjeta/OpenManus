"""Azure Code Interpreter Tool using Azure Container Apps dynamic sessions."""

import os
from typing import Dict, Optional, Any

import aiohttp
from pydantic import Field

from app.tool.base import BaseTool


class AzureCodeInterpreter(BaseTool):
    """
    A tool for executing Python code in isolated Azure Container Apps dynamic sessions.

    This tool leverages Azure's code interpreter sessions which provide secure isolated
    environments for executing potentially untrusted code.
    """

    name: str = "azure_code_interpreter"
    description: str = "Executes Python code securely in Azure Container Apps dynamic sessions. Ideal for running untrusted code or data processing tasks."
    parameters: dict = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute.",
            },
            "session_id": {
                "type": "string",
                "description": "Optional session ID to reuse an existing session. If not provided, a new session is created.",
            },
        },
        "required": ["code"],
    }

    pool_endpoint: str = Field(
        default=None,
        description="The management API endpoint for the session pool"
    )
    token_provider: Any = Field(
        default=None,
        description="Function or object that provides authentication tokens"
    )

    _current_session_id: Optional[str] = None
    _api_version: str = "2024-02-02-preview"

    async def execute(
        self,
        code: str,
        session_id: Optional[str] = None,
    ) -> Dict:
        """
        Executes the provided Python code in an Azure Code Interpreter session.

        Args:
            code (str): The Python code to execute.
            session_id (str, optional): Session ID to reuse. If None, uses or creates a session.

        Returns:
            Dict: Contains execution output and status.
        """
        if not self.pool_endpoint:
            return {
                "observation": "Error: Azure Code Interpreter not configured. Please set pool_endpoint.",
                "success": False,
            }

        # Use provided session_id, current session, or generate a new one
        session_id = session_id or self._current_session_id or f"session-{os.urandom(4).hex()}"
        self._current_session_id = session_id

        try:
            # Get authentication token
            token = await self._get_token()
            if not token:
                return {
                    "observation": "Error: Failed to get authentication token",
                    "success": False,
                }

            # Prepare the request
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }

            url = f"{self.pool_endpoint}/code/execute?api-version={self._api_version}&identifier={session_id}"
            payload = {
                "properties": {
                    "codeInputType": "inline",
                    "executionType": "synchronous",
                    "code": code
                }
            }

            # Execute the code
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    result = await response.json()

                    if response.status != 200:
                        return {
                            "observation": f"Error: {result.get('error', {}).get('message', 'Unknown error')}",
                            "success": False,
                        }

                    output = result.get("properties", {}).get("executionOutput", "")
                    return {
                        "observation": output,
                        "success": True,
                    }

        except Exception as e:
            return {
                "observation": f"Error executing code in Azure session: {str(e)}",
                "success": False,
            }

    async def upload_file(self, file_path: str, file_data: bytes, session_id: Optional[str] = None) -> Dict:
        """
        Uploads a file to the Azure Code Interpreter session.

        Args:
            file_path (str): Name to give the file in the session
            file_data (bytes): Binary content of the file
            session_id (str, optional): Session ID to use

        Returns:
            Dict: Result of the upload operation
        """
        session_id = session_id or self._current_session_id
        if not session_id:
            return {
                "observation": "Error: No active session. Execute code first or provide a session_id.",
                "success": False,
            }

        try:
            token = await self._get_token()
            url = f"{self.pool_endpoint}/files/upload?api-version={self._api_version}&identifier={session_id}"

            # Set up multipart form data
            form_data = aiohttp.FormData()
            form_data.add_field('file',
                                file_data,
                                filename=file_path,
                                content_type='application/octet-stream')

            headers = {
                "Authorization": f"Bearer {token}"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=form_data) as response:
                    if response.status != 200:
                        result = await response.json()
                        return {
                            "observation": f"Error uploading file: {result.get('error', {}).get('message', 'Unknown error')}",
                            "success": False,
                        }

                    return {
                        "observation": f"File {file_path} uploaded successfully",
                        "success": True,
                    }

        except Exception as e:
            return {
                "observation": f"Error uploading file: {str(e)}",
                "success": False,
            }

    async def _get_token(self) -> Optional[str]:
        """
        Gets an authentication token for the Azure API.

        Returns:
            str: Authentication token or None if not available
        """
        if callable(self.token_provider):
            return await self.token_provider()
        elif hasattr(self.token_provider, "get_token"):
            return await self.token_provider.get_token()
        return os.environ.get("AZURE_CODE_INTERPRETER_TOKEN")