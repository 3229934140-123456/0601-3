from setuptools import setup, find_packages

setup(
    name="esports-cli",
    version="1.0.0",
    description="电子竞技平台命令行工具 - 战队经理和赛事管理员的得力助手",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "rich>=13.7.0",
    ],
    entry_points={
        "console_scripts": [
            "esports=esports_cli.main:cli",
        ],
    },
    python_requires=">=3.8",
)
