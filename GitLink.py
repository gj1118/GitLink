import os
import re
import webbrowser
import sublime
import sublime_plugin
import subprocess

REMOTE_CONFIG = {
    'github': {
        'url': 'https://{5}/{0}/{1}/blob/{2}/{3}{4}',
        'line_param': '#L'
    },
    'bitbucket': {
        'url': 'https://bitbucket.org/{0}/{1}/src/{2}/{3}{4}',
        'line_param': '#cl-'
    },
    'codebasehq': {
        'url': 'https://{0}.codebasehq.com/projects/{1}/repositories/{2}/blob/{3}{4}/{5}',
        'line_param': '#L'
    }
}


class GitlinkCommand(sublime_plugin.TextCommand):

    def getoutput(self, command):
        out, err = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).communicate()
        return out.decode().strip()

    def run(self, edit, **args):
        # Current file path & filename

        # only works on current open file
        path, filename = os.path.split(self.view.file_name())

        # Switch to cwd of file
        os.chdir(path + "/")

        # Find the repo
        git_config_path = self.getoutput("git remote show origin -n")

        # Determine git URL which may be either HTTPS or SSH form
        # (i.e. https://domain/user/repo or git@domain:user/repo)
        #
        # parts[0][2] will contain 'domain/user/repo' or 'domain:user/repo'
        #
        # see https://regex101.com/r/pZ3tN3/2 & https://regex101.com/r/iS5tQ4/2
        p = re.compile(r"(.+: )*([\w\d\.]+)[:|@]/?/?(.*)")
        parts = p.findall(git_config_path)
        git_config = parts[0][2]

        if(":" in git_config) :
            remoteSite = git_config.split(":")[0]
        else:
            remoteSite = "github.com"

        remote_name = 'github'
        if 'bitbucket' in git_config:
            remote_name = 'bitbucket'
        if 'codebasehq.com' in git_config:
            remote_name = 'codebasehq'
        remote = REMOTE_CONFIG[remote_name]


        # need to get username from full url

        # Get username and repository (& also project for codebasehq)
        if ':' in git_config:
            # SSH repository
            if remote_name == 'codebasehq':
                # format is codebasehq.com:{user}/{project}/{repo}.git
                domain, user, project, repo = git_config.replace(".git", "").replace(":", "/").split("/")
            else:
                # format is {domain}:{user}/{repo}.git
                domain, user, repo = git_config.replace(".git", "").replace(":", "/").split("/")
        else:
            # HTTP repository
            if remote_name == 'codebasehq':
                # format is {user}.codebasehq.com/{project}/{repo}.git
                domain, project, repo = git_config.replace(".git", "").split("/")
                user = domain.split('.', 1)[0] # user is first segment of domain
            else:
                # format is {domain}/{user}/{repo}.git
                domain, user, repo = git_config.replace(".git", "").split("/")

        # Find top level repo in current dir structure
        remote_path = self.getoutput("git rev-parse --show-prefix")

        # Find the current revision
        rev_type = self.view.settings().get('gitlink_revision_type', 'branch')
        if rev_type == 'branch':
            git_rev = self.getoutput("git rev-parse --abbrev-ref HEAD")
        elif rev_type == 'commithash':
            git_rev = self.getoutput("git rev-parse HEAD")

        # Build the URL
        if remote_name == 'codebasehq':
            url = remote['url'].format(user, project, repo, git_rev, remote_path, filename)
        else:
            url = remote['url'].format(user, repo, git_rev, remote_path, filename, remoteSite)

        if(args['line']):
            region = self.view.sel()[0]
            first_line = self.view.rowcol(region.begin())[0] + 1
            last_line = self.view.rowcol(region.end())[0] + 1
            if first_line == last_line:
                url += "{0}{1}".format(remote['line_param'], first_line)
            else:
                url += "{0}{1}:{2}".format(remote['line_param'], first_line, last_line)

        if(args['web']):
            webbrowser.open_new_tab(url)
        else:
            sublime.set_clipboard(url)
            sublime.status_message('GIT url has been copied to clipboard')
