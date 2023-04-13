import os
from langchain import OpenAI, PromptTemplate, LLMChain
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains.mapreduce import MapReduceChain
from langchain.prompts import PromptTemplate

os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]

prompt = "This is a test"

def main() -> None:
    