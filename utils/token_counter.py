import tiktoken


def count_tokens(messages):
    try:
        encoding = tiktoken.encoding_for_model("gpt-4")
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    num_tokens = 0
    for message in messages:
        # Every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 4
        if hasattr(message, "content"):
            num_tokens += len(encoding.encode(str(message.content)))
    num_tokens += 2  # Every reply is primed with <im_start>assistant
    return num_tokens
