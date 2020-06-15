import setuptools

setuptools.setup(
    name="kanban-forecast-etl",
    version="0.0.1",
    auther="Grahame Gardiner",
    author_email="grahame.gardiner@limejump.com",
    description=(
        "A script for fetching kanban board data pertinent to forecasting"),
    packages=setuptools.find_packages(),
    install_requires=[
        'requests'
    ],
)
