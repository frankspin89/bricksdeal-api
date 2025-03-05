from setuptools import setup, find_packages

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
) 