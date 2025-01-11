from setuptools import setup, find_packages

setup(
    name="weather_dashboard",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.26.0",
        "requests>=2.28.0",
    ],
)