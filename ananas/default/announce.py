from ananas import PineappleBot, interval, schedule, ConfigurationError

class AnnounceBot(PineappleBot):
    """Bot that regularly checks approved users' feeds for posts with a
    particular hashtag and boosts them when found. Good for automated
    announcement bots which draw content from admins' feeds."""

    def init(self):
        self.config.hashtag = "announcement"
        self.config.allow_list = "admin"
        self.config.last_seen = 0

    def start(self):
        # Normalize the hashtag value
        if self.config.hashtag[0] == "#": self.config.hashtag = self.config.hashtag[1:]
        self.config.hashtag = self.config.hashtag.lower()

        # Tolerate not having actual lists in the underlying config
        if isinstance(self.config.allow_list, str):
            self.config.allow_list = [self.config.allow_list]

        if isinstance(self.config.last_seen, str):
            self.config.last_seen = [self.config.last_seen]

        # Make sure last seen ids are actually ints
        self.config.last_seen = [int(id) for id in self.config.last_seen]

        # Grab the actual user dicts for the usernames listed in the config
        self.users = []
        for username in self.config.allow_list:
            users = self.mastodon.account_search(username, 1)
            if len(users) == 0 or users[0].username.lower() != username:
                raise ConfigurationError("Unknown user {} in allow list".format(username))
            self.users.append(users[0])

        assert len(self.config.allow_list) == len(self.users)

        # Make sure the last seen array is the right length
        if len(self.config.last_seen) != len(self.config.allow_list):
            raise ConfigurationError("There must be the same number of last seen IDs as allowed users")

        # Run initial update immediately
        self.update()

    # Check every 1 minute
    #@interval(1 * 60)
    @schedule(minute="*/2", second="*")
    def update(self):
        self.log("debug", "Updating!")
        for i, user in enumerate(self.users):
            lowest_seen_this_time = self.config.last_seen[i]
            while (True):
                posts = self.mastodon.account_statuses(user, since_id=lowest_seen_this_time+1, exclude_replies=True)
                for post in posts:
                    post_id = post.id

                    if post.reblog:
                        post = post.reblog

                    for tag in post.tags:
                        if tag.name == self.config.hashtag:
                            self.log("debug", "BOOST: {}".format(post.id))
                            mastodon.status_reblog(post)
                            self.config.last_seen[i] = post_id
                            break

                if self.config.last_seen[i] == lowest_seen_this_time: break
                else: lowest_seen_this_time = self.config.last_seen[i]


