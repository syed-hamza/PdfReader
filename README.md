# ArxivQnA

ArxivQnA is a tool designed to help you search for and retrieve research papers from Arxiv using natural language queries. The tool leverages the OpenAI API to process your queries and fetch relevant papers. Please note that this tool is still under development, and you may experience errors or slow responses. Slow responses could also be due to the Arxiv API taking its time to process requests.

## TODO

- Prompt template
- conversational buffer(lllm for software)
- better retreival research

## Features

- Query research papers from Arxiv using natural language.
- Retrieve relevant papers based on your query.

## Prerequisites

- Python 3.x
- OpenAI API Key

## Installation

1. Clone this repository:

    ```bash
    git clone https://github.com/yourusername/ArxivQnA.git
    cd ArxivQnA
    ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Set up your OpenAI API key by either:

    1. Creating a `secretKey.json` file under the `scripts` directory and add the following data:

        ```json
        {
            "OpenAI": "Your Key"
        }
        ```

    2. Updating the code under `app/Libraries/graphAgentIndexing.py` to:

        ```python
        OPENAI_API_TOKEN = "YOUR_OPENAI_KEY"
        os.environ["OPENAI_API_KEY"] = OPENAI_API_TOKEN
        ```

## Usage

1. Navigate to the `app` directory:

    ```bash
    cd app
    ```

2. Run the application:

    ```bash
    python ./app.py
    ```

3. Follow the on-screen instructions to query and retrieve research papers from Arxiv.

## Notes

- Make sure your OpenAI API key is valid and has sufficient credits to run the queries.
- The tool is still under development, so you might encounter some bugs or slow responses.

## Contributing

We welcome contributions to improve ArxivQnA. If you have any suggestions or find any issues, please create an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Arxiv API](https://arxiv.org/help/api/index)
- [OpenAI API](https://beta.openai.com/docs/)

---

Feel free to reach out if you have any questions or need further assistance!
