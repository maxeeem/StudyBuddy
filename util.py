import os
import json

from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack import WebClient
from slack_bolt import App

from openai import OpenAI

OAI_TOKEN = os.environ["OAI_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]

local = True

base_url = "http://localhost:1234/v1" if local else "https://api.openai.com/v1"
api_key = "not-needed" if local else OAI_TOKEN
model = "local-model" if local else "gpt-4-turbo-preview"

oai_client = OpenAI(base_url=base_url, api_key=api_key)


def handle_event(client, uid, prompt, body):
    channel = body["event"]["channel"]    

    topic, timestamp, purpose = get_info(client, channel)
    
    history = [{"role": "system", "content": prompt(uid, topic, purpose)}]
    history += get_history(client, channel, timestamp, uid)
        
    response = oai_client.chat.completions.create(
        model=model,
        messages=history,
        temperature=0.7,
        stream=True,
#        n=3
    )
    
    new_message = {"role": "assistant", "content": " "}
    
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
            new_message["content"] += chunk.choices[0].delta.content
    
    new_message["content"] = new_message["content"].strip().removeprefix(f"<@{uid}>: ")

    response = client.chat_postMessage(channel=body["event"]["channel"],
                                       text=new_message['content'])


def log(response):
    print(json.dumps(response, indent=2))

def get_info(client, channel, debug=False):
    response = client.conversations_info(channel=channel)
    if debug:
       jstr = json.dumps(response.data, indent=2)
       print(jstr)
    
    topic = response["channel"]["topic"]["value"]
    topic_timestamp = response["channel"]["topic"]["last_set"]
    purpose = response["channel"]["purpose"]["value"]

    return (topic, topic_timestamp, purpose)

def get_history(client, channel, timestamp, uid, debug=False):
    response = client.conversations_history(channel=channel, oldest=timestamp)
    if debug:
        jstr = json.dumps(response.data, indent=2)
        print(jstr)
    
    history = []

    for message in reversed(response["messages"][:-1]):
        if message["type"] == "message":
            role = "assistant" if uid == message['user'] else "user"
            history.append({"role": role, "content": f'<@{message["user"]}>: {message["text"]}'})
            
    if debug:
        print(history)

    return history

