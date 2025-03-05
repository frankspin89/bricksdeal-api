from setuptools import setup, find_packages
import sys
import warnings

# Check Python version
if sys.version_info >= (3, 13):
    warnings.warn(
        "Python 3.13+ detected. This package is recommended for Python 3.8-3.12. "
        "Some dependencies may not be fully compatible with Python 3.13+.",
        RuntimeWarning
    )

setup(
    name="bricks-deal-crawl",
    version="0.1.0",
    description="LEGO data processing and catalog management tools",
    author="Frank Spin",
    author_email="frank@bricksdeal.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests",
        "beautifulsoup4",
        "pandas",
        "pillow",
        "cloudflare",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "bricks-deal=bricks_deal_crawl.main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 