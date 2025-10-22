"""Setup configuration for skai-fastmcp-cloudrun package."""

from setuptools import setup, find_packages

setup(
    name="skai-fastmcp-cloudrun",
    version="0.1.0",
    description="FastMCP server for Australian Hansard RAG with ChatGPT Developer Mode support",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "fastmcp>=2.12.5",
        "pydantic>=2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-asyncio>=0.21",
        ],
    },
)
