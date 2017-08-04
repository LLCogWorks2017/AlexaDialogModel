# Alexa Dialog Model


In this tutorial, we'll cover an approach to creating highly interactive Alexa skills that involve a series of many intents within the same conversation, and require a lot of slots to be filled.

## The Problem

For example, imagine an application that tells you when the next subway train is leaving, then can text you a reminder when it's time to leave. 

Example conversation:

```
User: When does the next train leave?
Alexa: What station?
User: Kendall
Alexa: What line?
User: Red
Alexa: What direction?
User: Inbound
Alexa: The next inbound Red Line train out of Kendall leaves at 5pm. Should I text you a reminder when it's time to leave?
User: Yes
Alexa: What is your phone number?
User: 555-555-5555
```

You can see that there are two intents embedded in this interaction: retrieving the train schedule and then scheduling a reminder. Each intent has an associated set of slots that must be filled to fully handle the request:

1. To retrieve the train schedle, we must know a) the intended station, b) the train line, and c) the direction (inbound or outbound).
2. To determine if the user wants a text message, we must know a) the user's phone number.

Obviously, performing these two intents independently is easy if all slots are filled:

```python
def get_next_train():
    direction = session.attributes["Direction"]
    line = session.attributes["Line"]
    station = session.attributes["Station"]
    time = 5  # In a real implementation, get this from the train schedule
    msg = "The next %s %s train from %s leaves in %i minutes." % (direction, line, station, time)
    return msg

def send_text():
    phone_number = session.attributes["PhoneNumber"]
    schedule_sms_message(phone_number)  # assume this is given
    msg = "OK, I've scheduled it"
    return msg
```

But what if a user hasn't specified all slots with a long, very specific utterance like: 

>"When does the next inbound Red Line train leave from Kendall Station? And please send me a text message reminder. My phone number is 555-555-5555." 

Expecting the user to know this exact template is not practical, and enumerating all possible ways a user might order the slots is messy. Instead, we want simple interactions like this:

>"When does the next train leave?

Or this:

>"When does the next train leave from Kendall?"

How can we control this interaction into a single, seamless conversation?

## Dialog Model

To solve these problems, we'll introduce the notion of a sequence of intents and their associated slots as a "dialog".

In Python, we can encode a dialog like this:

```python
dialog = [{"intent": get_next_train, "slots": schedule_slots, "transition_msg": "Should I text you?"}, 
          {"intent": send_text, "slots": text_slots, "transition_msg": None}]
```

Each element in the list is a python dictionary and holds 3 pieces of information:

1. An intent function object. This is the function that will execute when all slots are filled. For example, see the functions `get_next_train()` and `send_text()` above.
2. The necessary slots to accomplish the intent. We'll explain the structure of this next.
3. A "transition message". This is the text used to guide the conversation to the next intent. It's purpose will become more apparent later.

The `slots` data structure looks like this: 

```python
schedule_slots = [{"slot_name": "Station", "prompt": "What station?"},
        {"slot_name": "Line", "prompt": "What line?"},
        {"slot_name": "Direction", "prompt": "Inbound or outbound?"}]

text_slots = [{"slot_name": "PhoneNumber", "prompt": "What is your phone number?"}]
```

The list has one dictionary per slot. Each dictionary specifies a slot name and a prompt that asks the user a question to obtain the required information for the slot.

## Using the Dialog Model

So how do we actually use this dialog and slot model to build a skill? 

Conceptually, we can take the following approach.

* Iterate over the dialog elements and for each element, iterate over its required slots, and check whether or not the slot has been filled. When we encounter a missing slot, we can use the `prompt` string to ask the user for required information. Once all slots are filled, we can be sure the `intent` function can execute. After one intent has completed, we can use the `transition_msg` to bridge the conversation to the next intent. We then handle the next intent in the same manner as the first one.

As an example, let's assume we will use these sample utterances in our interaction model:

```
# sample utterances
NextTrainIntent when is the next {Line} train out of {Station}
NextTrainIntent when does the next train leave {Station}
NextTrainIntent when does the next train leave
```

Notice that no matter how many slots are uttered for `NextTrainIntent`, we still use the same function to handle the intent. That function would look like this:

```python
@ask.intent("NextTrainIntent")
def next_train(Station, Line):
    msg_type, msg = set_context_and_handle(None, None)
    
    if msg_type == "question":
        return question(msg)
    else:
        return statement(msg)
```

The ambiguity in undefined slots is handled by the `set_context_and_handle()` function:

```python
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

```

If a slot and its value are passed to this function, then the slot is stored in the `session` context of `flask_ask`. Then we iterate over the elements in the dialog and the slots: if the slot value exists in the `session.attributes` dictionary, we form a `question` with flask_ask and use the `prompt` string to ask the user for the slot's value. 

As a reminder, here is documentation on how [session attributes](https://alexatutorial.com/flask-ask/responses.html#session-management) work in `flask_ask`.

At this point, the question might try to fill the `Line` slot ask "What line?". The user would then speak one of the enumerated [custom slot](https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interaction-model-reference#custom-slot-syntax) values: `red|green|orange|blue`. These utterances are easily mapped to intents:

```
SetLineIntent {line}
```

And we can create an intent function for `SetLineIntent` that sets the slot value by using the `set_context_and_handle()` function again:

```python
@ask.intent("SetLineIntent")
def set_line(Line):
    msg_type, msg = set_context_and_handle("Line", Line)
    if msg_type == "question":
        return question(msg)
    else:
        return statement(msg)
```

This time, `set_context_and_handle()` is passed a slot name and a slot value, and it is assigned to the `session.attributes` dictionary. The code continues to handle missing slots in this manner until all slots are filled.

Once all slots are filled, `set_context_and_handle()` will then be able to execute the intent function. For example, Alexa would speak, "The next inbound Red Line train out of Kendall leaves at 5pm. Should I text you a reminder when it's time to leave?". Notice that the `transition_msg` is appended to the response, to guide the conversation to the next intent in the dialog.

So the `set_context_and_handle()` function is very general and can automatically guide the entire conversation. The entire "dialog" approach lets you keep your interaction model clean and build highly-interactive skills.