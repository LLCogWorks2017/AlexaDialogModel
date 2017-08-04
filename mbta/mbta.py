from flask import Flask
from flask_ask import Ask, statement, question, session
import requests
import time
import unidecode
import json

app = Flask(__name__)
ask = Ask(app, '/')


@ask.launch
def start_skill():
    msg = "Hello. What station are you leaving from?"
    return question(msg)


def get_next_train():
    direction = session.attributes["Direction"]
    line = session.attributes["Line"]
    station = session.attributes["Station"]
    time = 5
    msg = "The next %s %s train from %s leaves in %i minutes." % (direction, line, station, time)
    return msg


def send_text():
    pass


schedule_slots = [{"slot_name": "Station", "prompt": "What station?"},
                  {"slot_name": "Line", "prompt": "What line?"},
                  {"slot_name": "Direction", "prompt": "Inbound or outbound?"}]
dialog = [{"intent": get_next_train, "slots": schedule_slots, "transition_msg": "Should I text you?"},
          {"intent": send_text, "slots": None, "transition_msg": None}]


def set_context_and_handle(slot, value):
    """Set session attributes and form responses.
    
    Responses are either questions or statements, depending on whether all required slots have been filled.
    
    Args:
        slot (str or None): The name of the slot that we are filling. None if no slot to be filled.
        value (obj): The value of the slot.
    
    Returns:
        (str, str): The first string indicates the type of flask_ask response (either "question" or "statement").
        The second string is the message to speak to the user.
    """

    # set the slot value that we've received
    print("Got slot %s and value %s" % (slot, value))
    if slot and value:
        print("setting")
        session.attributes[slot] = value
        print("set %s" % session.attributes[slot])
        
    # iterate over intents in the dialog
    for seq in dialog:
        
        # iterate over slots
        intent_slots = seq["slots"]
        for s in intent_slots:

            # slot not filled if the value is not set in session
            if s["slot_name"] not in session.attributes:
                msg = s["prompt"]
                print("returning question %s" % msg)
                return "question", msg

        # all slots are filled at this point, so we can handle the intent
        final_msg = seq["intent"]()
        if seq["transition_msg"]:
            final_msg = final_msg + "..." + seq["transition_msg"]
            return "question", final_msg
        else:
            return "statement", final_msg


@ask.intent("NextTrainIntent")
def next_train(Station, Line):
    msg_type, msg = set_context_and_handle(None, None)
    if msg_type == "question":
        return question(msg)
    else:
        return statement(msg)


@ask.intent("SetStationIntent")
def set_station(Station):
    msg_type, msg = set_context_and_handle("Station", Station)
    if msg_type == "question":
        return question(msg)
    else:
        return statement(msg)


@ask.intent("SetLineIntent")
def set_line(Line):
    msg_type, msg = set_context_and_handle("Line", Line)
    if msg_type == "question":
        return question(msg)
    else:
        return statement(msg)


@ask.intent("SetDirectionIntent")
def set_line(Direction):
    msg_type, msg = set_context_and_handle("Direction", Direction)
    if msg_type == "question":
        return question(msg)
    else:
        return statement(msg)

@ask.intent("YesIntent")
def set_line():
    msg = "OK, I'll text you."
    return statement(msg)

@ask.intent("NoIntent")
def set_line():
    msg = "OK."
    return statement(msg)

if __name__ == '__main__':
    app.run(debug=True)

