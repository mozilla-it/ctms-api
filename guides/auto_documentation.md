# Steps for Auto-Documentation

1. Create an ssh key

    > ssh-keygen -t rsa -b 4096 -f ~/.ssh/gh-actions-{REPO}
2. Add the pubkey to a deploy key in github, name this key: sphinx-gh-actions
3. Add the private key to a Github Secret in the repo called `DEPLOY_KEY`
4. mkdir docs build
5. Add build to .gitignore
6. sphinx-quickstart -q -a 'A. Author <aauthor@example.com>' -v '0.0.1' --ext-autodoc --ext-coverage --ext-doctest --ext-githubpages -p containerized_microservice_template docs
7. sphinx-apidoc -f -o docs ./
8. Add the gh actions yaml to .github/workflows/
