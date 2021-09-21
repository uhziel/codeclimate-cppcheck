class Command:
    """Returns command line arguments by parsing codeclimate config file."""
    def __init__(self, config, file_list_path, file_path_type):
        self.config = config
        self.file_list_path = file_list_path
        self.file_path_type = file_path_type

    def build(self):
        command = ['cppcheck']

        if self.config.get('check'):
            command.append('--enable={}'.format(self.config.get('check')))

        if self.config.get('project'):
            command.append('--project={}'.format(self.config.get('project')))

        if self.config.get('language'):
            command.append('--language={}'.format(self.config.get('language')))

        for identifier in self.config.get('stds', []):
            command.append('--std={}'.format(identifier))

        if self.config.get('platform'):
            command.append('--platform={}'.format(self.config.get('platform')))

        for symbol in self.config.get('defines', []):
            command.append('-D{}'.format(symbol))

        for symbol in self.config.get('undefines', []):
            command.append('-U{}'.format(symbol))

        for directory in self.config.get('includes', []):
            command.append('-I{}'.format(directory))

        if self.config.get('max_configs'):
            if self.config.get('max_configs') == 'force':
                command.append('--force')
            else:
                command.append('--max-configs={}'.format(self.config.get('max_configs')))

        if self.config.get('inconclusive', 'true') == 'true':
            command.append('--inconclusive')
            
        if self.config.get('suppressions-list'):
            command.append('--suppressions-list={}'.format(self.config.get('suppressions-list')))
        
        if self.config.get('inline-suppr', 'false') == 'true':
            command.append('--inline-suppr')

        command.extend(['--xml', '--xml-version=2'])
        if self.file_path_type == 'checked_file':
            command.append(self.file_list_path)
        else:
            command.append('--file-list={}'.format(self.file_list_path))

        return command
