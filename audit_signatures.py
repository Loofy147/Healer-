import inspect
import os
import importlib.util
import sys
from typing import List, Dict, Any, Tuple, Optional, Set, Callable

def get_signatures(module_path):
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:
        return f"Could not load spec for {module_path}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        return f"Error loading {module_name}: {e}"

    results = []
    # Sort members by line number for better readability
    members = inspect.getmembers(module)

    classes = [obj for name, obj in members if inspect.isclass(obj) and obj.__module__ == module_name]
    functions = [obj for name, obj in members if inspect.isfunction(obj) and obj.__module__ == module_name]

    for obj in classes:
        results.append(f"### Class: `{obj.__name__}`")
        doc = inspect.getdoc(obj)
        if doc:
            results.append(f"_{doc.split('\n')[0]}_")

        methods = inspect.getmembers(obj, predicate=lambda x: inspect.isfunction(x) or inspect.ismethod(x))
        for m_name, m_obj in methods:
            if not m_name.startswith('_') or m_name == '__init__':
                try:
                    sig = inspect.signature(m_obj)
                    results.append(f"- `method` **{m_name}**`{sig}`")
                    m_doc = inspect.getdoc(m_obj)
                    if m_doc:
                        results.append(f"  - _{m_doc.split('\n')[0]}_")
                except Exception:
                    results.append(f"- `method` **{m_name}** (signature unavailable)")
        results.append("")

    for obj in functions:
        try:
            sig = inspect.signature(obj)
            results.append(f"### Function: `{obj.__name__}`")
            results.append(f"- `{obj.__name__}`**`{sig}`**")
            doc = inspect.getdoc(obj)
            if doc:
                results.append(f"  - _{doc.split('\n')[0]}_")
            results.append("")
        except Exception:
            results.append(f"### Function: `{obj.__name__}` (signature unavailable)")
            results.append("")

    return "\n".join(results)

files = [
    "fsc_framework.py",
    "fsc_structural.py",
    "fsc_binary.py",
    "fsc_network.py",
    "fsc_database.py",
    "fsc_storage.py",
    "fsc_domains.py"
]

with open("SYSTEM_SPEC.md", "w") as f:
    f.write("# FSC Universal Framework: System Specification\n\n")
    f.write("This document provides a comprehensive list of all classes, methods, and functions within the FSC framework.\n\n")
    for file_path in files:
        if os.path.exists(file_path):
            f.write(f"## Module: `{file_path}`\n\n")
            f.write(get_signatures(file_path))
            f.write("\n---\n\n")

print("SYSTEM_SPEC.md generated successfully.")
