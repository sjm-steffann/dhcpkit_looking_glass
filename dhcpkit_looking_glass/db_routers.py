"""
Route looking glass database stuff to dhcpkit_looking_glass
"""


class LookingGlassRouter(object):
    """
    A router to control all database operations on models in the
    dhcpkit_looking_glass application.
    """

    # noinspection PyUnusedLocal
    @staticmethod
    def db_for_read(model, **hints):
        """
        Attempts to read dhcpkit_looking_glass models go to dhcpkit_looking_glass.

        :param model: The database model
        :param hints: Any extra hints
        :return: database name or None
        """
        # noinspection PyProtectedMember
        if model._meta.app_label == 'dhcpkit_looking_glass':
            return 'dhcpkit_looking_glass'
        return None

    # noinspection PyUnusedLocal
    @staticmethod
    def db_for_write(model, **hints):
        """
        Attempts to write dhcpkit_looking_glass models go to dhcpkit_looking_glass.

        :param model: The database model
        :param hints: Any extra hints
        :return: database name or None
        """
        # noinspection PyProtectedMember
        if model._meta.app_label == 'dhcpkit_looking_glass':
            return 'dhcpkit_looking_glass'
        return None

    # noinspection PyUnusedLocal
    @staticmethod
    def allow_migrate(db, app_label, model=None, **hints):
        """
        The dhcpkit_looking_glass database is not managed by Django.

        :param db: The database name
        :param app_label: The app label
        :param model: The model
        :param hints: Any extra hints
        :return: Boolean
        """
        if app_label == 'dhcpkit_looking_glass' or db == 'dhcpkit_looking_glass':
            return False
        return None
