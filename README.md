# Remote VM Interactions Endpoint

Azure Functions HTTP endpoint that receives Discord interactions and starts an Azure VM on command.

## What it does

- Exposes `POST /api/discord-interactions`
- Verifies Discord request signatures (`X-Signature-Ed25519`, `X-Signature-Timestamp`)
- Handles Discord interaction types:
  - `type: 1` (ping) → returns verification response
  - `type: 2` with `/startserver` → checks VM power state and starts VM if needed
- Returns a Discord-compatible interaction callback message to the user

## Project structure

- `/home/runner/work/remote_vm_interactions_endpoint/remote_vm_interactions_endpoint/function_app.py` – main Azure Function and VM start logic
- `/home/runner/work/remote_vm_interactions_endpoint/remote_vm_interactions_endpoint/requirements.txt` – Python dependencies
- `/home/runner/work/remote_vm_interactions_endpoint/remote_vm_interactions_endpoint/host.json` – Azure Functions host settings
- `/home/runner/work/remote_vm_interactions_endpoint/remote_vm_interactions_endpoint/.github/workflows/main_palworld-discord-bot-24047.yml` – CI/CD workflow for build and deploy

## Requirements

- Python 3.13 (matches workflow)
- Azure Functions Core Tools (for local run)
- Azure credentials available to `DefaultAzureCredential` for VM read/start permissions

## Configuration

Set these environment variables:

- `DISCORD_PUBLIC_KEY` – Discord application public key
- `AZURE_SUBSCRIPTION_ID` – subscription containing the VM
- `AZURE_RESOURCE_GROUP` – VM resource group
- `AZURE_VM_NAME` – VM name to start
- `SERVER_ADDRESS` *(optional)* – shown in bot response, defaults to `98.70.34.20:8211`

## Local setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure Azure/Discord environment variables.
3. Start the function app:
   ```bash
   func start
   ```

The endpoint will be available at:

- `http://localhost:7071/api/discord-interactions`

## Discord command behavior

- If VM is already running, the bot replies with the configured server address.
- If VM is not running, the function sends an Azure start request and replies that startup has begun.
- If VM status/start fails, the bot returns a warning message and logs details in Function logs.

