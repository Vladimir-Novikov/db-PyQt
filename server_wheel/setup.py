from setuptools import setup

setup(
    name="server_app",
    version="1.0",
    description="Server",
    author="Vladimir Novikov",
    author_email="vovasnew@mail.ru",
    install_requires=[
        "SQLAlchemy==1.4.21",
    ],
    include_package_data=True,
    packages=["src"],
)
