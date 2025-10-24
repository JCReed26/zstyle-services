# 
# more so supposed to just be store for the users data for the session
#

class UserData():
    def __init__(self):
        self.user_id: str
                
    def _populate_user_data(self):
        """Meant to call backend to get stored api keys etc."""
        pass

    def _append_user_personalization_context(self):
        """adds user data collected for personalization"""
        pass