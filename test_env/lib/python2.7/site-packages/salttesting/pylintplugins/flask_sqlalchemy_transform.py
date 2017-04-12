# -*- coding: utf-8 -*-
'''
    :codeauthor: :email:`Pedro Algarvio (pedro@algarvio.me)`
    :copyright: © 2014 by the SaltStack Team, see AUTHORS for more details.
    :license: Apache 2.0, see LICENSE for more details.


    pylint_helpers
    ~~~~~~~~~~~~~~

    Help PyLint understand some of this projects parts
'''

from astroid import MANAGER
from astroid import nodes
from astroid.builder import AstroidBuilder


def flask_sqlalchemy_transform(module):
    if module.name != 'flask_sqlalchemy':
        return

    import flask_sqlalchemy
    flask_sqlalchemy._include_sqlalchemy(flask_sqlalchemy.SQLAlchemy)

    fake = AstroidBuilder(MANAGER).inspect_build(flask_sqlalchemy)

    for func_name, func in fake.locals.items():
        if func_name == 'SQLAlchemy':
            func[0].Model = fake.locals['Model'][0]
        module.locals[func_name] = func


def register(linter):
    '''
    Allow this to be setup when loading the plugins
    '''
    MANAGER.register_transform(nodes.Module, flask_sqlalchemy_transform)
