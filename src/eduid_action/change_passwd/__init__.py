from jinja2 import Environment, PackageLoader
from eduid_actions.action_abc import ActionPlugin


PACKAGE_NAME = 'eduid_action.change_passwd'


env = Environment(loader=PackageLoader(PACKAGE_NAME, 'templates'))


class ChangePasswdPlugin(ActionPlugin):

    steps = 1
    translations = {}

    @classmethod
    def get_translations(cls):
        return cls.translations

    def get_number_of_steps(self):
        return self.steps

    def get_action_body_for_step(self, step_number, action, request):
        lang = self.get_language(request)
        _ = self.translations[lang].ugettext
        template = env.get_template('main.jinja2')
        return template.render(_=_)

    def perform_action(self, action, request):
        lang = self.get_language(request)
        _ = self.translations[lang].ugettext
