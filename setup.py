from setuptools import setup, find_packages

setup(
    name="jemin",
    version="1.0.0",
    description="Jem In - a local, offline AI assistant for the terminal, powered by Ollama.",
    packages=find_packages(),
    install_requires=[
        "rich>=13.7.0",
        "requests>=2.31.0",
        "openai>=1.0.0",
        "anthropic>=0.30.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "jemin=jemin.app:main",
        ],
    },
)
