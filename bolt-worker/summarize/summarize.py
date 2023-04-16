import os
from langchain import OpenAI, PromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.docstore.document import Document
from langchain.chains.summarize import load_summarize_chain



llm = OpenAI(temperature=0)
text_splitter = CharacterTextSplitter()


def summarize(text: str, lang: str) -> dict:
    texts = text_splitter.split_text(text)
    docs = [Document(page_content=t) for t in texts]
    prompt_template = """Write a concise summary of the following:

{text}

CONCISE SUMMARY IN """ + lang + ":"
    PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
    chain = load_summarize_chain(OpenAI(temperature=0), chain_type="map_reduce", return_intermediate_steps=True, map_prompt=PROMPT, combine_prompt=PROMPT)
    return chain({"input_documents": docs}, return_only_outputs=True)
    