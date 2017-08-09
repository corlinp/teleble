# Teleble

Teleble is a web-based file sharing application. When visiting the homepage, a redirection is made to a user's unique bucket. From that link, a user can manage and share files in his bucket.


# Questions

* I pretty much implemented what I thought would be a cool, lightweight filesharing website. It (I hope) implements all the features that the prompt wanted.
* The biggest challenge was getting all the Javascript to work, as I have little experience in JS or Front end dev in general. the implementation of the guest link delete function would probably make a JS developer cry. But it works.
* The biggest limitation might be the lack of permission-granting to guest links, and the lack of file management options. These would not be too difficult to implement, but I thought I'd keep it simple.

### Security
I did put some thought into privacy and security so there are no obvious vulnerabilities I can point out aside from the simple lack of HTTPS. Security / Privacy really relies on the un-guessable nature of Version 4 UUIDs

* For real security we should include HTTPS, third-party and 2-factor authentication
* FineUploader (the JS file upload library) could have security vulnerabilities, that should be investigated


### Scalability
The current implementation of Teleble is not scalable beyond a few hundred users. While there shouldn't be any session conflicts, the included default Flask server is not recommended for real deployments (it's just barebones, no HTTPS or rate limiting or anything AFAIK). What we want to do is:

* Run Flask on a real web server like uWSGI and NGINX to act as a load balancer and static file host
* Turn it into a Docker application and use Rancher or the like to deploy instantly to multiple servers
* Optionally re-write the web server in Go, Erlang, or Java to achieve better performance per node

It is also problematic to store files directly on the filesystem, for a few reasons:

* If a user uploads a malicious file it has the potential to be run either accidentally or through some system process. One quick-fix to this might be to change all the extensions to .file or something, but that won't stop more advanced attackers.
* Most filesystems have a default 4KB block size, meaning if a user uploads a file smaller than that it will still take up 4KB on disk. This means a lot of small files can quickly fill up disk space.
* Filesystems are not easily shared or replicated across multiple servers (for horizontal scaling)

There are some nice solutions to this:

* Store small files (< 4 KB) in a KV-store like Riak
* Store large files in a distributed filesystem like GlusterFS
* Or host files on Amazon S3 and not worry about it

## Extensibility

One clear feature that could be added is a desktop client for dropbox-like sync functionality. Here's how I would implement it:

* One folder on a user's computer is designated as a 'Teleble' folder. A running service can use Java's WatchService API or similar to monitor that folder for changes. When a change occurs (add / change / delete file), it will be stored as a log in a local database.
* Each log in the local database of file changes will be associated with a time that action is performed. When internet is available, new changes will be applied to the 'master' that is running on the server and similarly propagated to other clients (folders on other computers that are synced to Teleble)

### Reducing operational costs
Aside from the already mentioned methods of scaling, it's probably a good idea to use a hosting provider that gives flexibility between RAM, SSD, and Disk. Files can then be dynamically allocated into one of those based on size and access frequency.

We should also place strict limits on users' bandwidth use and file size.

One may also fire all the programmers and move the company to China or the Philippines to hire cheap talent.