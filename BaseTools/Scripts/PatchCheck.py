#  Copyright (c) 2015 - 2019, Intel Corporation. All rights reserved.<BR>
            self.check_email_address(s[3])
    email_re1 = re.compile(r'(?:\s*)(.*?)(\s*)<(.+)>\s*$',
                           re.MULTILINE|re.IGNORECASE)

    def check_email_address(self, email):
        email = email.strip()
        mo = self.email_re1.match(email)
        if mo is None:
            self.error("Email format is invalid: " + email.strip())
            return

        name = mo.group(1).strip()
        if name == '':
            self.error("Name is not provided with email address: " +
                       email)
        else:
            quoted = len(name) > 2 and name[0] == '"' and name[-1] == '"'
            if name.find(',') >= 0 and not quoted:
                self.error('Add quotes (") around name with a comma: ' +
                           name)

        if mo.group(2) == '':
            self.error("There should be a space between the name and " +
                       "email address: " + email)

        if mo.group(3).find(' ') >= 0:
            self.error("The email address cannot contain a space: " +
                       mo.group(3))

        if count >= 1 and len(lines[0]) >= 72:
            self.error('First line of commit message (subject line) ' +
                       'is too long.')
                self.error('Line %d of commit message is too long.' % (i + 1))
                self.force_crlf = not self.filename.endswith('.sh')
        if '\t' in line:
        self.ok = msg_ok and diff_ok
        self.commit_subject = pmail['subject'].replace('\r\n', '')
        return self.run_git('show', '--pretty=email', '--no-textconv', commit)