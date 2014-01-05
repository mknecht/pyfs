pyfs
====

Mount python — it's fun, not a typo, and next to pointless!

*pyfs* is a [FUSE](http://fuse.sourceforge.net/) implementation that gives a filesystem view on [Python](http://www.python.org/) modules.

Why is that cool? You can do stuff like this:

    lib$ os/path/join /this is a path
    /this/is/a/path

Yes, that's `os.path.join` doing the work. Or look at this:

    lib$ string/capwords "let's do some python … not."
    Let's Do Some Python … Not.

Come on, that is cool, yes? Sure, it's a whee bit superfluous, a solution to no problem, but, hey, it'll get much better soon! Promise!

How does the root of the mountpoint look like? For example, like so:

    $ tree -L 2
    .
    ├── lib
    │   ├── __builtin__
    │   ├── json
    │   ├── os
    │   ├── string
    │   └── sys
    └── run
        └── modules
    
    7 directories, 1 file

Wonder what `run/modules` does? It's a file. You can `cat` it:

    $ cat run/modules 
    sys
    json
    os
    string
    __builtin__

But, you can also *add* modules:

    $ echo re >> run/modules 
	$ ls lib
	__builtin__  json  os  re  string  sys

And then you can use it:

	$ lib/re/match "\d+a" 33434a
	<_sre.SRE_Match object at 0x10641d0>

Or, you can get rid of the imported modules:

    $ echo > run/modules 
    $ ls lib/
    $ cat run/modules 
    $ 

The whole thing started, when I had [a look at Python's FUSE modules](http://mknecht.github.io/fuse-and-python/). If you want an overview about those, go over there.

== More weird ideas

* `$ lib/SimpleHttpServer/.self 8080   # python -m SimpleHttpServer 8080`
* `$ lib/re/match --help   # get the doc`
* provide symlinks for lib/__builtin__/*
* be able to use pipes: `$ echo blub | lib/re/match "\w" | lib/__builtin__/bool` (need to think about the shell always using strings, whereas some py functions expect other types …)
* access object methods (this sucks, a functional language would be much easier), i.e. $ lib/os/path/join my path | bin/dot count /
* provide a meta function to install packages in some virtualenv, so they can be loaded. (can I create a virtualenv at startup in memory and use that? /temp would be another option)

To be continued …
