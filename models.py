# models.py
# This file could contain class definitions for your data models if you
# were using an ORM like SQLAlchemy.  Since we're using raw SQL, it's
# less crucial here, but it's good practice to keep model-related code
# separate.
# We could put docstrings in here to describe the structure

class Link:
  """Represents a link to a folder.
  Attributes:
      id (int): The unique ID of the link.
      token (str): The random token for the link.
      folder_path (str): The path to the upload folder.
  """
  pass