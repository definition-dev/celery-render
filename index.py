import time
from flask import jsonify, Flask, request
import requests
from slack_sdk.signature import SignatureVerifier
import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL")

app = Flask(__name__)

SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET")

signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

# Celery configuration
def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=REDIS_URL,
        backend=REDIS_URL
    )
    celery.conf.update(app.config)
    
    # Task autodiscovery or manual registration
    celery.autodiscover_tasks([app.import_name])
    
    return celery

# Initialize Celery with Flask app context
celery = make_celery(app)

@celery.task(name="index.test_async")
def test_async(command):
    response_url = command.get('response_url')
    try:
        requests.post(response_url, json={"text": "Hello, World!", "response_type": "in_channel",})

        # Simulate some long-running task
        time.sleep(5)
        
        requests.post(response_url, json={"text": "Waiting for 5 seconds!", "response_type": "in_channel",})
    except Exception as e:
        print(f"Error sending message to response_url: {e}")


@app.route('/slack/commands', methods=['POST'])
def handle_commands():
    """
    Slack Commands API Endpoint

    This endpoint handles incoming slash commands from Slack.

    ---
    tags:
      - Slack
    parameters:
      - in: header
        name: X-Slack-Signature
        schema:
          type: string
        required: true
        description: Slack request signature for verification
      - in: header
        name: X-Slack-Request-Timestamp
        schema:
          type: string
        required: true
        description: Timestamp of the request
      - in: form
        name: command
        schema:
          type: string
        required: true
        description: The slash command that was invoked
      - in: form
        name: text
        schema:
          type: string
        required: false
        description: The text that was provided with the slash command
      - in: form
        name: channel_id
        schema:
          type: string
        required: true
        description: The ID of the channel where the command was invoked
    responses:
      200:
        description: Command processed successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                command:
                  type: object
                command_text:
                  type: string
                command_name:
                  type: string
                channel_id:
                  type: string
      403:
        description: Invalid request signature
        content:
          application/json:
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: invalid_request
    """
    if not signature_verifier.is_valid_request(request.get_data().decode('utf-8'), request.headers):
        return jsonify({'status': 'invalid_request'}), 403

    # Acknowledge Slack's command immediately to avoid timeouts
    command = request.form
    test_async.delay(command)
    # executor.submit(test_async(command))

    # Return an immediate acknowledgment to Slack to avoid timeout
    return jsonify("We are finding your insights, give us a moment :grimacing:"), 200
