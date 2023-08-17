from setuptools import setup

setup(
    name="burf",
    version="1.0.7",
    packages=["burf"],
    install_requires=["textual==0.28.1", "google-cloud-storage==2.10.0"],
    entry_points={"console_scripts": ["burf=burf.burf:main"]},
    author="Mohammad Razeghi",
    author_email="razeghi71@gmail.com",
    description="A tool to surf buckets on gcs",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/razeghi71/burf",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)
