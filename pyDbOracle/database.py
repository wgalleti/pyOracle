import cx_Oracle
from dj_database_url import parse

from pyDbOracle.errors import OracleMakeTnsError, OracleConnectionError, OracleCommandError


class Database:

    def __init__(self, string, auto_connect=True):
        self.connection = None
        self.rac = False
        self.tns = None
        self._make_tns_string(string)

        if auto_connect:
            self.connect(rac=True)

    def _make_tns_string(self, string):
        try:
            dbenv = parse(string)

            self.user = dbenv.get('USER')
            self.pwd = dbenv.get('PASSWORD')
            host = dbenv.get('HOST')
            port = dbenv.get('PORT')
            service = dbenv.get('NAME')
            options = dbenv.get('OPTIONS')

            if isinstance(options, dict):
                self.rac = bool(options.get('threaded', False))

            self.tns = cx_Oracle.makedsn(host, port, service_name=service)
        except Exception as e:
            raise OracleMakeTnsError(f'Error on make tns string. Erro: {e}')

    def connect(self, rac=False):
        try:
            self.connection = cx_Oracle.connect(self.user, self.pwd, self.tns, threaded=self.rac)
        except cx_Oracle.DatabaseError as e:
            raise OracleConnectionError(f'Error on connect database.\n {self.tns}\nUSER: {self.user}\nERROR: {e}')

    def disconnect(self):
        try:
            self.connection.close()
        except:
            pass

    def get(self, **kwargs):

        command = kwargs.get('command', '')
        params = kwargs.get('params', [])
        extract_one = kwargs.get('extract_one', True)

        if 'select' not in command.lower():
            raise OracleCommandError('SQL command incorrect')

        try:
            cursor = self.connection.cursor()
            cursor.execute(command, params)
            columns = [col[0].lower() for col in cursor.description]

            data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()

            for i in enumerate(data):
                for c in columns:
                    if type(data[i[0]][c]) == cx_Oracle.LOB:
                        data[i[0]][c] = data[i[0]][c].read()

            if len(data) == 1 and extract_one:
                return data[0]

            return data
        except Exception as e:
            raise OracleCommandError(e)

    def run(self, **kwargs):
        command = kwargs.get('command', '')
        params = kwargs.get('params', [])
        commit = kwargs.get('commit', True)

        commands_accepteds = ['insert', 'update', 'delete']

        for i in commands_accepteds:
            if i not in command.lower():
                raise OracleCommandError('SQL Command invalid')

        try:
            cursor = self.connection.cursor()
            cursor.execute(command, params)
            if commit:
                self.connection.commit()
        except cx_Oracle.DatabaseError as e:
            raise OracleCommandError(e)
        else:
            return cursor.rowcount

    def info(self):
        SQL = """
          SELECT VERSION AS VERSAO, STARTUP_TIME AS INICIADO_EM, PARALLEL AS PARALELISMO, BLOCKED AS BLOQUEADO 
          FROM V$INSTANCE
        """
        if self.connection is None:
            return dict(connected=False,
                        tns=self.tns,
                        user=self.user,
                        versao='',
                        iniciado_em=None,
                        paralelismo=False,
                        bloqueado=False)

        try:
            data = self.get(command=SQL)
        except OracleCommandError as e:
            return dict(connected=False,
                        tns=self.tns,
                        user=self.user,
                        versao='',
                        iniciado_em=None,
                        paralelismo=False,
                        bloqueado=False,
                        error=e)
        else:
            data['connected'] = True
            data['tns'] = self.tns
            data['user'] = self.user
            data['paralelismo'] = True if data['paralelismo'] == 'YES' else False
            data['bloqueado'] = True if data['bloqueado'] == 'YES' else False

        return data
