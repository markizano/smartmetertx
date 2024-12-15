Run this to start up the local server.
Configure with `~/.config/smartmetertx/config.yml`.
Starts on port 7689 by default.

Passwords are encrypted using gpg. You can store the PGP armored message block in your configuration
file and this app will attempt to decrypt using your key (pending you manage the password/key/chain requirements beyond this app).

Encrypt the password using:

    $ echo -en "my-secret-password" | gpg -aer 0x0000

Where `0x0000` is the key you want to use for this encryption.
In this way, sensitive credentials are not stored in plain text in files.

Loads a simple web page that can be used to visualize the data you want.

For more info on how `config.yml` works, please see [config.yml.md](./config.yml.md)
