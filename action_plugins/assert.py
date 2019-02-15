from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
from ansible.errors import AnsibleError
from ansible.playbook.conditional import Conditional
from ansible.plugins.action import ActionBase


class ActionModule(ActionBase):
    ''' Fail with custom message '''

    TRANSFERS_FILES = False

    def __init__(self, *args, **kwargs):
        super(ActionModule, self).__init__(*args, **kwargs)

        self.fail_verbose = (
            os.environ.get(
            'ASSERTIVE_FAIL_VERBOSE', '0').lower()
            in ['1', 'yes', 'true'])

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if 'that' not in self._task.args:
            raise AnsibleError('conditional required in "that" string')

        msg = None
        if 'msg' in self._task.args:
            msg = self._task.args['msg']
        elif 'fail_msg' in self._task.args:
            msg = self._task.args['fail_msg']

        # make sure the 'that' items are a list
        thats = self._task.args['that']
        if not isinstance(thats, list):
            thats = [thats]

        # Now we iterate over the that items, temporarily assigning them
        # to the task's when value so we can evaluate the conditional using
        # the built in evaluate function. The when has already been evaluated
        # by this point, and is not used again, so we don't care about mangling
        # that value now
        cond = Conditional(loader=self._loader)
        results = []

        for that in thats:
            cond.when = [that]
            test_result = cond.evaluate_conditional(templar=self._templar, all_vars=task_vars)

            result = {
                'assertion': that,
                'evaluated_to': bool(test_result),
            }

            results.append(result)

        failed = any(not result['evaluated_to'] for result in results)
        changed_when_failed = not self._task.args.get('fatal', False)

        ret = {
            'assertions': results,
            'changed': (failed and changed_when_failed),
            'failed': (failed and not changed_when_failed),
            'ansible_stats': {
                'data': {
                    'assertions': 1,
                    'assertions_failed': 1 if failed else 0,
                    'assertions_passed': 0 if failed else 1,
                },
                'aggregate': True,
                'per_host': True,
            },
        }

        if failed and self.fail_verbose:
            ret['_ansible_verbose_always'] = True

        if failed and msg:
            ret['msg'] = msg
        elif not failed:
            ret['msg'] = 'All assertions passed'

        return ret
