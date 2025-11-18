import os
import subprocess


def run(cmd: list[str]) -> int:
    print("$", " ".join(cmd))
    # Use python -m babel instead of pybabel directly
    if cmd[0] == 'pybabel':
        cmd = ['python', '-m', 'babel.messages.frontend'] + cmd[1:]
    return subprocess.call(cmd)


def main():
    # Requires Flask-Babel/Babel installed
    os.makedirs('translations', exist_ok=True)
    # Extract messages
    run(['pybabel', 'extract', '-F', 'babel.cfg', '-o', 'messages.pot', '.'])

    # Initialize languages if not already
    languages = ['en', 'nl', 'de', 'fr', 'it', 'fi', 'es', 'ar', 'he', 'nb']
    for lang in languages:
        po_dir = os.path.join('translations', lang, 'LC_MESSAGES')
        po_path = os.path.join(po_dir, 'messages.po')
        if not os.path.exists(po_path):
            run(['pybabel', 'init', '-i', 'messages.pot', '-d', 'translations', '-l', lang])
    # Update catalogs
    run(['pybabel', 'update', '-i', 'messages.pot', '-d', 'translations'])
    # Compile
    run(['pybabel', 'compile', '-d', 'translations'])


if __name__ == '__main__':
    main()


