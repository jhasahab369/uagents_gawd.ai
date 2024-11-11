import json
from chitchat import ChitChatDialogue
from ai_engine.messages import DialogueMessage, BaseMessage
from uagents import Agent, Context, Model, Field
from groq import Groq


class InitiateChitChatDialogue(Model):
    # This class represents the initiation message for the chit-chat dialogue.
    assistant_type: str = Field(
        description='You MUST ask the user what type of assistant they are looking for. This is the type of assistant you are looking for.'
    )
    model: str = Field(
        description="You MUST always ask the user which LLM model they want to choose from these options: 'gemma-7b-it', 'gemma2-9b-it', 'llama3-8b-8192', 'llama3-groq-70b-8192-tool-use-preview', 'llava-v1.5-7b-4096-preview', 'whisper-large-v3', 'mixtral-8x7b-32768'. Remember, you MUST provide these as options, and the user has to select one."
    )


class AcceptChitChatDialogue(BaseMessage):
    # This class represents an accepted dialogue message.
    type: str = "agent_message"
    # User messages, this is the text that the user wants to send to the agent
    agent_message: str


class ChitChatDialogueMessage(DialogueMessage):
    # This class represents a chit-chat dialogue message.
    """ChitChat dialogue message"""
    pass


class ConcludeChitChatDialogue(Model):
    # This class represents the conclusion of a chit-chat dialogue.
    """I conclude ChitChat dialogue request"""
    pass


class RejectChitChatDialogue(Model):
    # This class represents a rejection of the chit-chat dialogue.
    """I reject ChitChat dialogue request"""
    pass


async def generate_response(assistant, user_input, model):
    # Function to generate a response using the selected LLM model from Groq API
    client = Groq(api_key="")

    # Define the system prompt for the assistant
    system_prompt = {
        "role": "system",
        "content": f"You are a {assistant}. You reply with very short answers."
    }

    # Initialize the chat history with the system prompt
    chat_history = [system_prompt]
    # Add the user input to the chat history
    chat_history.append({"role": "user", "content": user_input})

    # Call the Groq API to generate a response
    response = client.chat.completions.create(
        model=model,
        messages=chat_history,
        max_tokens=100,
        temperature=1.2
    )

    # Append the assistant's response to the chat history
    chat_history.append({
        "role": "assistant",
        "content": response.choices[0].message.content
    })

    # Return the generated response
    return response.choices[0].message.content


mailbox_key = ''

# Initialize the agent with the name, seed, mailbox, and log level
agent = Agent(
    name="groq-example-agent",
    seed="hilesgo",
    mailbox=f"{mailbox_key}@https://agentverse.ai",
    log_level="DEBUG",
)

# Instantiate the chit-chat dialogue and assign it to the agent's storage
chitchat_dialogue = ChitChatDialogue(
    version="0.66",
    storage=agent.storage,
)



#handlers---------------------------


@chitchat_dialogue.on_initiate_session(InitiateChitChatDialogue)
async def start_chitchat(
    ctx: Context,
    sender: str,
    msg: InitiateChitChatDialogue,
):
    # Log that an initiation message was received
    ctx.logger.info(f"Received init message from {sender} Session: {ctx.session}")
    # Store assistant type and model selected by the user in the session storage
    ctx.storage.set('Assistant', msg.assistant_type)
    ctx.storage.set('Model', msg.model)
    # Send an acceptance message to the sender, introducing the assistant and model
    await ctx.send(
        sender, 
        AcceptChitChatDialogue(agent_message=f"Hello, I am your {msg.assistant_type} assistant and I am running on LLM Model {msg.model}")
    )

# Handler for when the chit-chat dialogue is accepted
@chitchat_dialogue.on_start_dialogue(AcceptChitChatDialogue)
async def accepted_chitchat(
    ctx: Context,
    sender: str,
    _msg: AcceptChitChatDialogue,
):
    # Log that the session was accepted by the agent
    ctx.logger.info(
        f"Session with {sender} was accepted. This shouldn't be called as this agent is not the initiator."
    )

# Handler for when the chit-chat dialogue is rejected
@chitchat_dialogue.on_reject_session(RejectChitChatDialogue)
async def reject_chitchat(
    ctx: Context,
    sender: str,
    _msg: RejectChitChatDialogue,
):
    # Log that the dialogue was rejected
    ctx.logger.info(f"Received conclude message from: {sender}")

# Handler for when the chit-chat dialogue continues
@chitchat_dialogue.on_continue_dialogue(ChitChatDialogueMessage)
async def continue_chitchat(
    ctx: Context,
    sender: str,
    msg: ChitChatDialogueMessage,
):
    # Log the received message from the sender
    ctx.logger.info(f"Received message: {msg.user_message} from: {sender}")
    
    # Retrieve the assistant type and model stored in the session
    type = ctx.storage.get('Assistant')
    model = ctx.storage.get('Model')
    
    # Log the user's selection of assistant type and model
    ctx.logger.info(f'User selected the {type} type of assistant with model: {model}.')
    
    # Generate a response using the specified model
    response = await generate_response(type, msg.user_message, model)
    
    try:
        # Send the generated response back to the sender
        await ctx.send(
            sender,
            ChitChatDialogueMessage(
                type="agent_message",
                agent_message=response
            ),
        )
    except EOFError:
        # Handle end of file error by sending a conclude message
        await ctx.send(sender, ConcludeChitChatDialogue())

# Handler for when the chit-chat dialogue is concluded
@chitchat_dialogue.on_end_session(ConcludeChitChatDialogue)
async def conclude_chitchat(
    ctx: Context,
    sender: str,
    _msg: ConcludeChitChatDialogue,
):
    # Log that the dialogue is concluded and access the dialogue history
    ctx.logger.info(f"Received conclude message from: {sender}; accessing history:")
    ctx.logger.info(ctx.dialogue)

agent.include(chitchat_dialogue, publish_manifest=True)

if __name__ == "__main__":
    # Print the agent's address to confirm it's running
    print(f"Agent address: {agent.address}")
    # Run the agent
    agent.run()