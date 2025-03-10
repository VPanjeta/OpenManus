
# Azure Code Interpreter



The Azure Code Interpreter tool allows secure execution of Python code in isolated environments using Azure Container Apps dynamic sessions. This is particularly useful for running untrusted code or for data processing tasks that require a secure and scalable environment.



## Features



-  **Secure Code Execution**: Runs Python code in isolated containers

-  **Session Management**: Maintains state between multiple code executions

-  **File Upload Support**: Upload data files to use in your code

-  **Preinstalled Packages**: Common data science and ML libraries are preinstalled



## Setup



### 1. Create an Azure Container Apps Session Pool



#### Install the Azure CLI (if not installed)

Please  follow  Microsoft  Azure  CLI  installation  guide: [Azure CLI  Installation](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli-macos)

First, you need to create a session pool in Azure:



```bash


# Upgrade the Azure CLI

az  upgrade



# Install or upgrade the Azure Container Apps extension

az  extension  add  --name  containerapp  --upgrade  --allow-preview  true  -y



# Create a session pool

az  containerapp  sessionpool  create  \

--name my-session-pool \

--resource-group <RESOURCE_GROUP> \

--location westus2 \

--container-type  PythonLTS  \

--max-sessions 100 \

--cooldown-period  300  \

--network-status EgressDisabled

```



### 2. Get the Session Pool Management Endpoint



```bash

az  containerapp  sessionpool  show  \

--name my-session-pool \

--resource-group <RESOURCE_GROUP> \

--query 'properties.poolManagementEndpoint' -o tsv

```



### 3. Configure Authentication



Ensure your application has proper authentication:



1. Create a managed identity for your application

2. Assign the identity these roles on the session pool:

- "Azure ContainerApps Session Executor"

- "Contributor"



### 4. Update Configuration



Add the Azure Code Interpreter configuration to your `config.toml` file:



```toml

[azure_code_interpreter]

pool_endpoint = "https://<REGION>.dynamicsessions.io/subscriptions/<SUBSCRIPTION_ID>/resourceGroups/<RESOURCE_GROUP>/sessionPools/<SESSION_POOL_NAME>"

token_env_var = "AZURE_CODE_INTERPRETER_TOKEN"

```



## Usage Examples



### Basic Code Execution



```python

result =  await agent.available_tools.execute(

name="azure_code_interpreter",

tool_input={

"code": """

import numpy as np

import matplotlib.pyplot as plt



# Generate random data

data = np.random.randn(1000)



# Create histogram

plt.hist(data, bins=30)

plt.title('Normal Distribution')



# Print statistics

print(f"Mean: {data.mean():.4f}")

print(f"Std Dev: {data.std():.4f}")

print(f"Min: {data.min():.4f}")

print(f"Max: {data.max():.4f}")

"""

}

)

print(result["observation"])

```



### Uploading and Processing Files



```python

# First, read a file

with  open("data.csv", "rb") as f:

file_data = f.read()



# Upload the file to the session

azure_interpreter = agent.available_tools.get_tool("azure_code_interpreter")

await azure_interpreter.upload_file("data.csv", file_data)



# Now process the file in the session

result =  await agent.available_tools.execute(

name="azure_code_interpreter",

tool_input={

"code": """

import pandas as pd

import matplotlib.pyplot as plt



# Read the uploaded file

df = pd.read_csv('/mnt/data/data.csv')



# Show basic info

print(f"Data shape: {df.shape}")

print("\nFirst 5 rows:")

print(df.head())



# Basic statistics

print("\nBasic statistics:")

print(df.describe())

"""

}

)

print(result["observation"])

```



### Session Reuse



```python

# Execute first code block

result1 =  await agent.available_tools.execute(

name="azure_code_interpreter",

tool_input={

"code": """

import numpy as np



# Create data in the session

data = np.random.rand(100, 5)

np.save('/mnt/data/my_data.npy', data)

print("Data saved to file")

"""

}

)



# Get the session ID from the first execution

session_id = agent.available_tools.get_tool("azure_code_interpreter")._current_session_id



# Execute second code block in the same session

result2 =  await agent.available_tools.execute(

name="azure_code_interpreter",

tool_input={

"code": """

import numpy as np



# Load the data that was saved in the previous code block

loaded_data = np.load('/mnt/data/my_data.npy')

print(f"Loaded data shape: {loaded_data.shape}")

print(f"First 3 rows:\n{loaded_data[:3]}")

""",

"session_id": session_id

}

)

```



## Security Considerations



- By default, network egress is disabled, preventing code from accessing external resources

- Sessions are isolated using Hyper-V containers

- Sessions automatically terminate after the configured cooldown period

- Consider using custom container images with only the packages you need

- For highly sensitive data, configure private networking



## Troubleshooting



If you encounter issues:



1.  **Authentication Errors**: Verify your token is valid and has the correct audience claim

2.  **Session Not Found**: Sessions may expire after the cooldown period

3.  **Resource Limits**: Check if you've hit the maximum sessions limit

4.  **Network Issues**: For code requiring internet access, ensure egress is enabled



Edit `config.toml` to set up your:

- LLM provider (OpenAI, Azure, etc.)

- Azure Code Interpreter (if using)

- Other optional configurations

