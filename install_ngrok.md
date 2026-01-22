# About Ngrok

ngrok allows for rapid tunneling, exposing local servers behind NATs and firewalls to the public internet over secure tunnels. More information in https://ngrok.com/

# Installing ngrok

ngrok 1.x is unmaintained and its usage is not encouraged. Instead, follow the instructions on https://ngrok.com/download

1. download the zip file. In my case is for ubuntu_64 16.04

```
$ cd ~/Downloads
$ wget https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip
```
2. Unzip the file and get a binary file.

## Using the recommended defaults

move the binary file to `/usr/local/bin`. Since this is in the `$PATH` defaults should now work.

## Alias ngrok from `.bashrc` 

You can put ngrok anywhere. An example folder is `ngrok` in my `/home` folder.

```
$ cd
$ mkdir ngrok && cd ngrok
$ cp $(ls ~/Downloads/ngrok*) ~/ngrok/
$ unzip ngrok-file.zip 
```
then make an alias in `~/.bashrc`

```
$ echo "# ngrok alias" >> ~/.bashrc
$ echo "alias ngrok='full/path/to/ngrok/binary'" >> ~/.bashrc
$ . ~/.bashrc
```

You should be able to run `ngrok` from anywhere

```
$ ngrok --version
ngrok version 2.2.8
```


# Using ngrok with Vagrant

Next step is getting an ngrok account and set identity keys locally. Check ngrok documentation after creating a new account.
From vagrant root, run `vagrant share`.  You should be getting something like

```
Vagrant Share now defaults to using the `ngrok` driver.
The `classic` driver has been deprecated.

For more information about the `ngrok` driver, please
refer to the documentation:

  https://www.vagrantup.com/docs/share/

==> default: Detecting network information for machine...
    default: Local machine address: 127.0.0.1
    default:  
    default: Note: With the local address (127.0.0.1), Vagrant Share can only
    default: share any ports you have forwarded. Assign an IP or address to your
    default: machine to expose all TCP ports. Consult the documentation
    default: for your provider ('virtualbox') for more information.
    default:  
    default: Local HTTP port: 4567
    default: Local HTTPS port: disabled
    default: Port: 2222
    default: Port: 4567
==> default: Creating Vagrant Share session...
==> default: HTTP URL: http://c23c2fce.ngrok.io
==> default: 
```

http://c23c2fce.ngrok.io is a random generated url and should be different each time. In my case I'm serving using apache defaults.

```
$ curl http://c23c2fce.ngrok.io

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html>
 <head>
  <title>Index of /</title>
 </head>
 <body>
<h1>Index of /</h1>
<table><tr><th><img src="/icons/blank.gif" alt="[ICO]"></th><th><a href="?C=N;O=D">Name</a></th><th><a href="?C=M;O=A">Last modified</a></th><th><a href="?C=S;O=A">Size</a></th><th><a href="?C=D;O=A">Description</a></th></tr><tr><th colspan="5"><hr></th></tr>
<tr><td valign="top"><img src="/icons/unknown.gif" alt="[   ]"></td><td><a href="Vagrantfile">Vagrantfile</a></td><td align="right">02-Apr-2018 01:40  </td><td align="right">3.1K</td><td>&nbsp;</td></tr>
<tr><td valign="top"><img src="/icons/text.gif" alt="[TXT]"></td><td><a href="bootstrap.sh">bootstrap.sh</a></td><td align="right">02-Apr-2018 01:27  </td><td align="right">139 </td><td>&nbsp;</td></tr>
<tr><th colspan="5"><hr></th></tr>
</table>
<address>Apache/2.2.22 (Ubuntu) Server at c23c2fce.ngrok.io Port 80</address>
</body></html>
```

# Sharing an existing app outside of vagrant

* Fire up your app normally. For Flask default applications, these are served from 127.0.0.1:5000
* Launch `ngrok` in another terminal

```
$ ngrok http 5000
```

* ???
* profit (share your url)