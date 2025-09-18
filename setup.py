from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="slideshow-generator",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automated slideshow generator with text animations and audio sync",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/slideshow-generator",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Video :: Display",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "tts": ["gtts>=2.2.0", "pydub>=0.25.1"],
        "dev": ["pytest>=6.0", "pytest-cov", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "slideshow-generator=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml", "data/*.txt"],
    },
)