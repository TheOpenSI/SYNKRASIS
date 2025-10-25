    def add_language(self, language):
        """"Add new language for item translations."""
        if self.connection:
            self.cursor.execute('insert into itemlanguage (language) values ("%s")' % language[0])
            self.connection.commit()