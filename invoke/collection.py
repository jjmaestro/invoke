import types

from .vendor.lexicon import Lexicon

from .parser import Context, Argument
from .tasks import Task


class Collection(object):
    """
    A collection of executable tasks.
    """
    def __init__(self, *args, **kwargs):
        """
        Create a new task collection/namespace.

        May call with no arguments and use e.g. `.add_task`/`.add_collection` to insert objects, e.g.::

            c = Collection()
            c.add_task(some_task)

        If an initial string argument is given, it is used as the default name
        for this collection, should it be inserted into another collection as a
        sub-namespace::

            docs = Collection('docs')
            docs.add_task(doc_task)
            ns = Collection()
            ns.add_task(top_level_task)
            ns.add_collection(docs)
            # Valid identifiers are now 'top_level_task' and 'docs.doc_task'
            # (assuming the task objects were actually named the same as the
            # variables we're using :))

        Otherwise, all ``*args`` are expected to be `.Task` or `.Collection`
        instances which will be passed to `.add_task`/`.add_collection` as
        appropriate. Module objects are also valid (as they are for
        `.add_collection`). For example, the below snippet results in the same
        two task identifiers as the one above::

            ns = Collection(top_level_task, Collection('docs', doc_task))

        If any ``**kwargs`` are given, the keywords are used as the initial
        name arguments for the respective values::

            ns = Collection(
                top_level_task=some_other_task,
                docs=Collection(doc_task)
            )

        That's exactly equivalent to::

            docs = Collection(doc_task)
            ns = Collection()
            ns.add_task(some_other_task, 'top_level_task')
            ns.add_collection(docs, 'docs')
        """
        # Initialize
        self.tasks = Lexicon()
        self.collections = Lexicon()
        self.default = None
        self.name = None
        # Name if applicable
        args = list(args)
        if args and isinstance(args[0], basestring):
            self.name = args.pop(0)
        # Dispatch args/kwargs
        for arg in args:
            self._add_object(arg)
        # Dispatch kwargs
        for name, obj in kwargs.iteritems():
            self._add_object(obj, name)

    def _add_object(self, obj, name=None):
        if isinstance(obj, Task):
            method = self.add_task
        elif isinstance(obj, (Collection, types.ModuleType)):
            method = self.add_collection
        else:
            raise TypeError("No idea how to insert %r!" % type(obj))
        return method(obj, name=name)

    def add_task(self, task, name=None, aliases=(), default=False):
        """
        Adds ``Task`` ``task`` to this collection.

        If ``name`` is not explicitly given (recommended) the ``.func_name`` of
        the ``Task``'s wrapped callable will be used instead. (If the wrapped
        callable is not a function, you *must* give ``name``.)

        If ``aliases`` is given, will be used to set up additional aliases for
        this task.

        ``default`` may be set to ``True`` to set the task as this collection's
        default invocation.
        """
        if name is None:
            if hasattr(task.body, 'func_name'):
                name = task.body.func_name
            else:
                raise ValueError("'name' may only be empty if 'task' wraps an object exposing .func_name")
        self.tasks[name] = task
        for alias in aliases:
            self.tasks.alias(alias, to=name)
        if default:
            if self.default:
                msg = "'%s' cannot be the default because '%s' already is!"
                raise ValueError(msg % (name, self.default))
            self.default = name

    def add_collection(self, coll, name=None):
        # Handle module-as-collection
        if isinstance(coll, types.ModuleType):
            coll = Collection.from_module(coll)
        # Ensure we have a name, or die trying
        name = name or coll.name
        if not name:
            raise ValueError("Non-root collections must have a name!")
        # Insert
        self.collections[name] = coll

    def __getitem__(self, name=None):
        """
        Returns task named ``name``. Honors aliases and subcollections.

        If this collection has a default task, it is returned when ``name`` is
        empty or ``None``. If empty input is given and no task has been
        selected as the default, ValueError will be raised.

        Tasks within subcollections should be given in dotted form, e.g.
        'foo.bar'.
        """
        if not name:
            if self.default:
                return self[self.default]
            else:
                raise ValueError("This collection has no default task.")
        if '.' in name:
            parts = name.split('.')
            coll = parts.pop(0)
            rest = '.'.join(parts)
            return self.collections[coll][rest]
        return self.tasks[name]

    def __contains__(self, name):
        return name in self.tasks

    def to_contexts(self):
        """
        Returns all contained tasks and subtasks as a list of parser contexts.
        """
        # TODO: this is now a stub, do away w/ it
        result = []
        for name, task in self.tasks.iteritems():
            result.append(Context(
                name=name, aliases=task.aliases, args=task.get_arguments()
            ))
        return result
