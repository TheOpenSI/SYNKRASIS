class ServiceBase:
    """
    Base class for all services
    """
    def __init__(self):
        """
        prints a message when the service is started
        """
        print(f"Starting the {self.__class__.__name__} service...")