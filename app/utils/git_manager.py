from git import Repo

class GitManager:
    def __init__(self, repo_url, repo_path):
        self.repo_url = repo_url
        self.repo_path = repo_path

    def clone(self):
        Repo.clone_from(self.repo_url, self.repo_path)

    def pull(self):
        repo = Repo(self.repo_path)
        repo.remotes.origin.pull()

    def checkout(self, branch):
        repo = Repo(self.repo_path)
        repo.git.checkout(branch)

    def branch(self, branch):
        repo = Repo(self.repo_path)
        repo.git.branch(branch)
        repo.git.checkout(branch)