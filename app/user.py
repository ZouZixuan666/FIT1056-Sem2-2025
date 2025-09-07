class User:
    """A base class for all users in the system."""
    def __init__(self, id, name):  # accept id, not user_id
        self.id = id
        self.name = name

    def __repr__(self):
        return f"<User {self.id}: {self.name}>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name
        }