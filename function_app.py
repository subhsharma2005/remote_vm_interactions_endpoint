import os
import json
import logging

import azure.functions as func
import requests
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

DISCORD_PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ["AZURE_RESOURCE_GROUP"]
VM_NAME = os.environ["AZURE_VM_NAME"]
SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "98.70.34.20:8211")

_credential = DefaultAzureCredential()


def verify_discord_signature(req: func.HttpRequest) -> bool:
    signature = req.headers.get("X-Signature-Ed25519", "")
    timestamp = req.headers.get("X-Signature-Timestamp", "")
    body = req.get_body().decode("utf-8")
    try:
        verify_key = VerifyKey(bytes.fromhex(DISCORD_PUBLIC_KEY))
        verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
        return True
    except (BadSignatureError, ValueError):
        return False


def start_vm() -> bool:
    token = _credential.get_token("https://management.azure.com/.default")
    url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Compute"
        f"/virtualMachines/{VM_NAME}/start?api-version=2024-07-01"
    )
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {token.token}"},
        timeout=10,
    )
    logging.info("Azure start call returned %s", resp.status_code)
    return resp.status_code in (200, 202)


def get_vm_power_state() -> str:
    token = _credential.get_token("https://management.azure.com/.default")
    url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Compute"
        f"/virtualMachines/{VM_NAME}/instanceView?api-version=2024-07-01"
    )
    resp = requests.get(url, headers={"Authorization": f"Bearer {token.token}"}, timeout=10)
    resp.raise_for_status()
    statuses = resp.json().get("statuses", [])
    for s in statuses:
        code = s.get("code", "")
        if code.startswith("PowerState/"):
            return code.split("/", 1)[1]
    return "unknown"


@app.route(route="discord-interactions", methods=["POST"])
def discord_interactions(req: func.HttpRequest) -> func.HttpResponse:
    if not verify_discord_signature(req):
        return func.HttpResponse("Invalid request signature", status_code=401)

    body = req.get_json()
    interaction_type = body.get("type")

    # Discord's endpoint verification ping - must echo type 1 back.
    if interaction_type == 1:
        return func.HttpResponse(json.dumps({"type": 1}), mimetype="application/json")

    if interaction_type == 2:
        command_name = body.get("data", {}).get("name")

        if command_name == "startserver":
            try:
                power_state = get_vm_power_state()
            except Exception:
                logging.exception("Failed to read VM power state")
                power_state = "unknown"

            if power_state == "running":
                message = f"✅ Server's already running. Connect to `{SERVER_ADDRESS}`."
            else:
                try:
                    ok = start_vm()
                except Exception:
                    logging.exception("Failed to start VM")
                    ok = False

                if ok:
                    message = (
                        f"🟢 Starting the Palworld server! Give it a minute or two, "
                        f"then connect to `{SERVER_ADDRESS}`."
                    )
                else:
                    message = "⚠️ Couldn't start the VM - check the Function logs."

            return func.HttpResponse(
                json.dumps({"type": 4, "data": {"content": message}}),
                mimetype="application/json",
            )

        return func.HttpResponse(
            json.dumps({"type": 4, "data": {"content": "Unknown command."}}),
            mimetype="application/json",
        )

    return func.HttpResponse(status_code=400)
