"""
Setup configuration for Omnilingual Language Finder
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="omnilingual-finder",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Find language codes for Meta's Omnilingual ASR in seconds",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/omnilingual-finder",
    packages=find_packages(exclude=["tests", "examples", "scripts"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: Linguistic",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Zero runtime dependencies!
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=22.0",
            "flake8>=4.0",
            "mypy>=0.950",
        ],
        "build": [
            "httpx>=0.24",
            "pandas>=1.5",
            "requests>=2.28",
        ],
    },
    entry_points={
        "console_scripts": [
            "omnilingual-finder=finder.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "finder": ["py.typed"],
    },
    keywords=[
        "language",
        "speech-recognition",
        "asr",
        "multilingual",
        "nlp",
        "omnilingual",
        "language-codes",
        "iso-639",
        "linguistics",
    ],
    project_urls={
        "Bug Reports": "https://github.com/yourusername/omnilingual-finder/issues",
        "Source": "https://github.com/yourusername/omnilingual-finder",
        "Documentation": "https://github.com/yourusername/omnilingual-finder#readme",
    },
)