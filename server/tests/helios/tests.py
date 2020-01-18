"""
Unit Tests for Helios
"""

import re
import uuid

import django_webtest
import pytest
from django.conf import settings
from django.core import mail
from django.core.files import File
from django.test import TestCase
from django.utils.html import escape as html_escape
from django.utils.timezone import now

import helios.datatypes as datatypes
import helios.models as models
import helios.utils as utils
import helios.views as views
from helios_auth import models as auth_models


@pytest.mark.django_db
class ElectionModelTests(TestCase):
    fixtures = ["users.json"]
    allow_database_queries = True

    def create_election(self):
        return models.Election.get_or_create(
            short_name="demo",
            name="Demo Election",
            description="Demo Election Description",
            admin=self.user,
        )

    def setup_questions(self):
        QUESTIONS = [
            {
                "answer_urls": [None, None, None],
                "answers": ["a", "b", "c"],
                "choice_type": "approval",
                "max": 1,
                "min": 0,
                "question": "w?",
                "result_type": "absolute",
                "short_name": "w?",
                "tally_type": "homomorphic",
            }
        ]
        self.election.questions = QUESTIONS

    def setup_trustee(self):
        self.election.generate_trustee(views.ELGAMAL_PARAMS)

    def setup_openreg(self):
        self.election.openreg = True
        self.election.save()

    def setUp(self):
        self.user = auth_models.User.objects.get(
            user_id="ben@adida.net", user_type="google"
        )
        self.fb_user = auth_models.User.objects.filter(user_type="facebook")[0]
        self.election, self.created_p = self.create_election()

    def test_create_election(self):
        assert self.created_p is True

        assert self.election.created_at is not None
        assert self.election.created_at < now()

    def test_find_election(self):
        election = models.Election.get_by_user_as_admin(self.user)[0]
        assert self.election == election

        election = models.Election.get_by_uuid(self.election.uuid)
        assert self.election == election

        election = models.Election.get_by_short_name(self.election.short_name)
        assert self.election == election

    def test_setup_trustee(self):
        self.setup_trustee()
        assert self.election.num_trustees == 1

    def test_add_voters_file(self):
        election = self.election

        with open("helios/fixtures/voter-file.csv") as file:
            vf = models.VoterFile.objects.create(
                election=election, voter_file=File(file, "voter_file.css")
            )

            vf.process()

        # make sure that we stripped things correctly
        voter = election.voter_set.get(voter_login_id="benadida5")
        assert voter.voter_email == "ben5@adida.net"
        assert voter.voter_name == "Ben5 Adida"

    def test_check_issues_before_freeze(self):
        # should be three issues: no trustees, and no questions, and no voters
        issues = self.election.issues_before_freeze
        assert len(issues) == 3

        self.setup_questions()

        # should be two issues: no trustees, and no voters
        issues = self.election.issues_before_freeze
        assert len(issues) == 2

        self.election.questions = None

        self.setup_trustee()

        # should be two issues: no questions, and no voters
        issues = self.election.issues_before_freeze
        assert len(issues) == 2

        self.setup_questions()

        # move to open reg
        self.setup_openreg()

        issues = self.election.issues_before_freeze
        assert not len(issues)

    def test_helios_trustee(self):
        self.election.generate_trustee(views.ELGAMAL_PARAMS)

        assert self.election.has_helios_trustee()

        trustee = self.election.get_helios_trustee()
        assert trustee is not None

    def test_log(self):
        LOGS = ["testing 1", "testing 2", "testing 3"]

        for log in LOGS:
            self.election.append_log(log)

        pulled_logs = [l.log for l in self.election.get_log().all()]

        assert LOGS == list(reversed(pulled_logs))

    def test_eligibility(self):
        self.election.eligibility = [{"auth_system": self.user.user_type}]

        # without openreg, this should be false
        assert not self.election.user_eligible_p(self.user)

        # what about after saving?
        self.election.save()
        e = models.Election.objects.get(uuid=self.election.uuid)
        assert e.eligibility == [{"auth_system": self.user.user_type}]


        self.election.openreg = True

        # without openreg, and now true
        assert self.election.user_eligible_p(self.user)

        # try getting pretty eligibility, make sure it doesn't throw an exception
        assert self.user.user_type in self.election.pretty_eligibility

    def test_freeze(self):
        # freezing without trustees and questions, no good

        with pytest.raises(Exception):
            self.election.freeze()

        self.setup_questions()
        self.setup_trustee()
        self.setup_openreg()

        # this time it should work
        self.election.freeze()

        # make sure it logged something
        assert self.election.get_log().exists()

    def test_archive(self):
        self.election.archived_at = now()
        assert self.election.is_archived

        self.election.archived_at = None
        assert not self.election.is_archived

    def test_voter_registration(self):
        # before adding a voter
        voters = models.Voter.get_by_election(self.election)
        assert not voters

        # make sure no voter yet
        voter = models.Voter.get_by_election_and_user(self.election, self.user)
        assert voter is None

        # make sure no voter at all across all elections
        voters = models.Voter.get_by_user(self.user)
        assert not voters

        # register the voter
        voter = models.Voter.register_user_in_election(self.user, self.election)

        # make sure voter is there now
        voter_2 = models.Voter.get_by_election_and_user(self.election, self.user)
        assert voter
        assert voter_2
        assert voter == voter_2

        # make sure voter is there in this call too
        voters = models.Voter.get_by_user(self.user)
        assert list(voters) == [voter]

        voter_2 = models.Voter.get_by_election_and_uuid(self.election, voter.uuid)
        assert voter == voter_2
        assert voter.user == self.user


class VoterModelTests(TestCase):
    fixtures = ["users.json", "election.json"]
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.get(short_name="test")

    def test_create_password_voter(self):
        v = models.Voter(
            uuid=str(uuid.uuid1()),
            election=self.election,
            voter_login_id="voter_test_1",
            voter_name="Voter Test 1",
            voter_email="foobar@acme.com",
        )
        v.generate_password()
        v.save()

        # password has been generated!
        assert v.voter_password is not None

        # can't generate passwords twice
        with pytest.raises(Exception):
            v.generate_password()

        # check that you can get at the voter user structure
        assert v.get_user().user_id == v.voter_email


class CastVoteModelTests(TestCase):
    fixtures = ["users.json", "election.json"]
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.get(short_name="test")
        self.user = auth_models.User.objects.get(
            user_id="ben@adida.net", user_type="google"
        )

        # register the voter
        self.voter = models.Voter.register_user_in_election(
            self.user, self.election)

    # def test_cast_vote(self):
    #     pass


class DatatypeTests(TestCase):
    fixtures = ["users.json", "election.json"]
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.election.generate_trustee(views.ELGAMAL_PARAMS)

    def test_instantiate(self):
        ld_obj = datatypes.LDObject.instantiate(
            self.election.get_helios_trustee(), "2011/01/Trustee"
        )
        foo = ld_obj.serialize()

    @staticmethod
    def test_from_dict():
        ld_obj = datatypes.LDObject.fromDict(
            {"y": "1234", "p": "23434", "g": "2343243242", "q": "2343242343434"},
            type_hint="pkc/elgamal/PublicKey",
        )

    @staticmethod
    def test_dictobject_from_dict():
        original_dict = {"A": "35423432", "B": "234324243"}
        ld_obj = datatypes.LDObject.fromDict(
            original_dict, type_hint="legacy/EGZKProofCommitment"
        )

        assert original_dict == ld_obj.toDict()


##
# Black box tests
##


class DataFormatBlackboxTests(TestCase):
    def setUp(self):
        self.election = models.Election.objects.all()[0]

    def assertEqualsToFile(self, response, file_path):
        expected = open(file_path)
        assert response.content == expected.read()
        expected.close()

    #
    # def test_election(self):
    #     response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
    #     self.assertEqualsToFile(response, self.election)

    # def test_election_metadata(self):
    #     response = self.client.get("/helios/elections/%s/meta" % self.election.uuid, follow=False)
    #     self.assertEqualsToFile(response, self.EXPECTED_ELECTION_METADATA_FILE)
    #
    # def test_voters_list(self):
    #     response = self.client.get("/helios/elections/%s/voters/" % self.election.uuid, follow=False)
    #     self.assertEqualsToFile(response, self.EXPECTED_VOTERS_FILE)
    #
    # def test_trustees_list(self):
    #     response = self.client.get("/helios/elections/%s/trustees/" % self.election.uuid, follow=False)
    #     self.assertEqualsToFile(response, self.EXPECTED_TRUSTEES_FILE)
    #
    # def test_ballots_list(self):
    #     response = self.client.get("/helios/elections/%s/ballots/" % self.election.uuid, follow=False)
    #     self.assertEqualsToFile(response, self.EXPECTED_BALLOTS_FILE)


# now we have a set of fixtures and expected results for various formats
# note how TestCase is used as a "mixin" here, so that the generic DataFormatBlackboxTests
# does not register as a set of test cases to run, but each concrete data format does.


class LegacyElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
    fixtures = ["legacy-data.json"]
    allow_database_queries = True
    EXPECTED_ELECTION_FILE = "helios/fixtures/legacy-election-expected.json"
    EXPECTED_ELECTION_METADATA_FILE = (
        "helios/fixtures/legacy-election-metadata-expected.json"
    )
    EXPECTED_VOTERS_FILE = "helios/fixtures/legacy-election-voters-expected.json"
    EXPECTED_TRUSTEES_FILE = "helios/fixtures/legacy-trustees-expected.json"
    EXPECTED_BALLOTS_FILE = "helios/fixtures/legacy-ballots-expected.json"


# class V3_1_ElectionBlackboxTests(DataFormatBlackboxTests, TestCase):
#    fixtures = ['v3.1-data.json']
#    EXPECTED_ELECTION_FILE = 'helios/fixtures/v3.1-election-expected.json'
#    EXPECTED_VOTERS_FILE = 'helios/fixtures/v3.1-election-voters-expected.json'
#    EXPECTED_TRUSTEES_FILE = 'helios/fixtures/v3.1-trustees-expected.json'
#    EXPECTED_BALLOTS_FILE = 'helios/fixtures/v3.1-ballots-expected.json'


class WebTest(django_webtest.WebTest):
    def assertStatusCode(self, response, status_code):
        if hasattr(response, "status_code"):
            assert response.status_code == status_code, response.status_code
        else:
            assert response.status_int == status_code, response.status_int

    def assertRedirects(self, response, url):
        """
        reimplement this in case it's a WebOp response
        and it seems to be screwing up in a few places too
        thus the localhost exception
        """
        if hasattr(response, "location"):
            assert url in response.location, response.location
        else:
            assert url in response["location"], response["location"]
        self.assertStatusCode(response, 302)
        # return super(django_webtest.WebTest, self).assertRedirects(response, url)
        # assert url in response.location, "redirected to %s instead of %s" % (response.location, url)

    def assertContains(self, response, text):
        self.assertStatusCode(response, 200)

        if hasattr(response, "testbody"):
            assert text in response.testbody, "missing text %s" % text
        elif hasattr(response, "body"):
            assert text in response.body, "missing text %s" % text
        else:
            assert text in response.content, "missing text %s" % text


##
# overall operation of the system
##


class ElectionBlackboxTests(WebTest):
    fixtures = ["users.json", "election.json"]
    allow_database_queries = True

    def setUp(self):
        self.election = models.Election.objects.all()[0]
        self.user = auth_models.User.objects.get(
            user_id="ben@adida.net", user_type="google"
        )

    def setup_login(self, from_scratch=False, **kwargs):
        if from_scratch:
            # a bogus call to set up the session
            self.client.get("/")
        # set up the session
        session = self.client.session
        if kwargs:
            user = auth_models.User.objects.get(**kwargs)
        else:
            user = self.user
        session["user"] = {"type": user.user_type, "user_id": user.user_id}
        session.save()

        # set up the app, too
        # this does not appear to work, boohoo
        # session = self.app.session
        # session['user'] = {'type': self.user.user_type, 'user_id': self.user.user_id}

    def clear_login(self):
        session = self.client.session
        del session["user"]
        session.save()

    def test_election_params(self):
        response = self.client.get("/helios/elections/params")
        self.assertEquals(
            response.content.decode(), views.ELGAMAL_PARAMS_LD_OBJECT.serialize()
        )

    # returns 301 for some reason and then 404
    # def test_election_404(self):
    #     response = self.client.get("/helios/elections/foobar")
    #     self.assertStatusCode(response, 404)

    def test_election_bad_trustee(self):
        response = self.client.get(
            "/helios/t/%s/foobar@bar.com/badsecret" % self.election.short_name
        )
        assert response.status_code == 404

    def test_get_election_shortcut(self):
        response = self.client.get(
            "/helios/e/%s" % self.election.short_name, follow=True
        )
        assert self.election.description in response.content.decode()

    # also redirection problem
    # def test_get_election_raw(self):
    #     response = self.client.get("/helios/elections/%s" % self.election.uuid, follow=False)
    #     assert self.election.toJSON() in response.content.decode()

    def test_get_election(self):
        response = self.client.get(
            "/helios/elections/%s/view" % self.election.uuid, follow=False
        )
        assert self.election.description in response.content.decode()

    def test_get_election_questions(self):
        response = self.client.get(
            "/helios/elections/%s/questions" % self.election.uuid, follow=False
        )
        for q in self.election.questions:
            assert q["question"] in response.content.decode()

    def test_get_election_trustees(self):
        response = self.client.get(
            "/helios/elections/%s/trustees" % self.election.uuid, follow=False
        )
        for t in self.election.trustee_set.all():
            assert t.name in response.content.decode()

    def test_get_election_voters(self):
        response = self.client.get(
            "/helios/elections/%s/voters/list" % self.election.uuid, follow=False
        )
        # check total count of voters
        if self.election.num_voters == 0:
            assert "no voters" in response.content.decode()
        else:
            assert "(of %s)" % self.election.num_voters in response.content.decode()

    def test_get_election_voters_raw(self):
        response = self.client.get(
            "/helios/elections/%s/voters/" % self.election.uuid, follow=False
        )
        assert (
            len(utils.from_json(response.content.decode())) == self.election.num_voters
        )

    def test_election_creation_not_logged_in(self):
        response = self.client.post(
            "/helios/elections/new",
            {
                "short_name": "test-complete",
                "name": "Test Complete",
                "description": "A complete election test",
                "election_type": "referendum",
                "use_voter_aliases": "0",
                "use_advanced_audit_features": "1",
                "private_p": "False",
            },
        )

        self.assertRedirects(response, "/auth/?return_url=/helios/elections/new")

    def test_election_edit(self):
        self.setup_login(from_scratch=True)
        response = self.client.get("/helios/elections/%s/edit" % self.election.uuid)
        response = self.client.post(
            "/helios/elections/%s/edit" % self.election.uuid,
            {
                "short_name": self.election.short_name + "-2",
                "name": self.election.name,
                "description": self.election.description,
                "election_type": self.election.election_type,
                "use_voter_aliases": self.election.use_voter_aliases,
                "csrf_token": self.client.session["csrf_token"],
            },
        )

        self.assertRedirects(response, "/helios/elections/%s/view" % self.election.uuid)

        new_election = models.Election.objects.get(uuid=self.election.uuid)
        self.assertEquals(new_election.short_name, self.election.short_name + "-2")

    # def test_get_election_stats(self):
    #     self.setup_login(from_scratch=True, user_id='mccio@github.com', user_type='google')
    #     response = self.client.get("/helios/stats/", follow=False)
    #     self.assertStatusCode(response, 200)
    #     response = self.client.get("/helios/stats/force-queue", follow=False)
    #     self.assertRedirects(response, "/helios/stats/")
    #     response = self.client.get("/helios/stats/elections", follow=False)
    #     self.assertStatusCode(response, 200)
    #     response = self.client.get("/helios/stats/problem-elections", follow=False)
    #     self.assertStatusCode(response, 200)
    #     response = self.client.get("/helios/stats/recent-votes", follow=False)
    #     self.assertStatusCode(response, 200)
    #     self.clear_login()
    #     response = self.client.get("/helios/stats/", follow=False)
    #     self.assertStatusCode(response, 403)
    #     self.setup_login()
    #     response = self.client.get("/helios/stats/", follow=False)
    #     self.assertStatusCode(response, 403)
    #     self.clear_login()

    def _setup_complete_election(self, election_params=None):
        "do the setup part of a whole election"

        # REPLACE with params?
        self.setup_login(from_scratch=True)

        # create the election
        full_election_params = {
            "short_name": "test-complete",
            "name": "Test Complete",
            "description": "A complete election test",
            "election_type": "referendum",
            "use_voter_aliases": "0",
            "use_advanced_audit_features": "1",
            "private_p": "False",
            "csrf_token": self.client.session["csrf_token"],
        }

        # override with the given
        full_election_params.update(election_params or {})

        response = self.client.post(
            "/helios/elections/new", full_election_params)

        # we are redirected to the election, let's extract the ID out of the URL
        election_id = re.search(
            "/elections/([^/]+)/", str(response["Location"]))
        self.assertIsNotNone(
            election_id,
            "Election id not found in redirect: %s" % str(
                response["Location"]),
        )
        election_id = election_id.group(1)

        # helios is automatically added as a trustee

        # check that helios is indeed a trustee
        response = self.client.get(
            "/helios/elections/%s/trustees/view" % election_id)
        self.assertContains(response, "Trustee #1")

        # add a few voters with an improperly placed email address
        FILE = "helios/fixtures/voter-badfile.csv"
        voters_file = open(FILE)
        response = self.client.post(
            "/helios/elections/%s/voters/upload" % election_id,
            {"voters_file": voters_file},
        )
        voters_file.close()
        self.assertContains(response, "HOLD ON")

        # add a few voters, via file upload
        # this file now includes a UTF-8 encoded unicode character
        # yes I know that's not how you spell Ernesto.
        # I just needed some unicode quickly.
        FILE = "helios/fixtures/voter-file.csv"
        voters_file = open(FILE)
        response = self.client.post(
            "/helios/elections/%s/voters/upload" % election_id,
            {"voters_file": voters_file},
        )
        voters_file.close()
        self.assertContains(response, "first few rows of this file")

        # now we confirm the upload
        response = self.client.post(
            "/helios/elections/%s/voters/upload" % election_id, {
                "confirm_p": "1"}
        )
        self.assertRedirects(
            response, "/helios/elections/%s/voters/list" % election_id)

        # and we want to check that there are now voters
        response = self.client.get(
            "/helios/elections/%s/voters/" % election_id)
        NUM_VOTERS = 4
        self.assertEquals(len(utils.from_json(response.content)), NUM_VOTERS)

        # let's get a single voter
        single_voter = models.Election.objects.get(
            uuid=election_id).voter_set.all()[0]
        response = self.client.get(
            "/helios/elections/%s/voters/%s" % (election_id, single_voter.uuid)
        )
        self.assertContains(response, '"uuid": "%s"' % single_voter.uuid)

        response = self.client.get(
            "/helios/elections/%s/voters/foobar" % election_id)
        self.assertStatusCode(response, 404)

        # add questions
        response = self.client.post(
            "/helios/elections/%s/save_questions" % election_id,
            {
                "questions_json": utils.to_json(
                    [
                        {
                            "answer_urls": ["http://example.com", None],
                            "answers": ["Alice", "Bob"],
                            "choice_type": "approval",
                            "max": 1,
                            "min": 0,
                            "question": "Who should be president?",
                            "result_type": "absolute",
                            "short_name": "Who should be president?",
                            "tally_type": "homomorphic",
                        }
                    ]
                ),
                "csrf_token": self.client.session["csrf_token"],
            },
        )

        self.assertContains(response, "SUCCESS")

        # freeze election
        response = self.client.post(
            "/helios/elections/%s/freeze" % election_id,
            {"csrf_token": self.client.session["csrf_token"]},
        )
        self.assertRedirects(
            response, "/helios/elections/%s/view" % election_id)

        # email the voters
        num_messages_before = len(mail.outbox)
        response = self.client.post(
            "/helios/elections/%s/voters/email" % election_id,
            {
                "csrf_token": self.client.session["csrf_token"],
                "subject": "your password",
                "body": "time to vote",
                "suppress_election_links": "0",
                "send_to": "all",
            },
        )
        self.assertRedirects(
            response, "/helios/elections/%s/view" % election_id)
        num_messages_after = len(mail.outbox)
        self.assertEquals(num_messages_after - num_messages_before, NUM_VOTERS)

        email_message = mail.outbox[num_messages_before]
        assert "your password" in email_message.subject, "bad subject in email"

        # get the username and password
        username = re.search("voter ID: (.*)", email_message.body).group(1)
        password = re.search("password: (.*)", email_message.body).group(1)

        # now log out as administrator
        self.clear_login()
        self.assertEquals(self.client.session.has_key("user"), False)

        # return the voter username and password to vote
        return election_id, username, password

    def _cast_ballot(
        self,
        election_id,
        username,
        password,
        need_login=True,
        check_user_logged_in=False,
    ):
        """
        check_user_logged_in looks for the "you're already logged" message
        """
        # vote by preparing a ballot via the server-side encryption
        response = self.app.post(
            "/helios/elections/%s/encrypt-ballot" % election_id,
            params={"answers_json": utils.to_json([[1]])},
        )
        self.assertContains(response, "answers")

        # parse it as an encrypted vote with randomness, and make sure randomness is there
        the_ballot = utils.from_json(response.testbody)
        assert the_ballot["answers"][0].has_key("randomness"), "no randomness"
        assert len(the_ballot["answers"][0]["randomness"]
                   ) == 2, "not enough randomness"

        # parse it as an encrypted vote, and re-serialize it
        ballot = datatypes.LDObject.fromDict(
            utils.from_json(response.testbody), type_hint="legacy/EncryptedVote"
        )
        encrypted_vote = ballot.serialize()

        # cast the ballot
        response = self.app.post(
            "/helios/elections/%s/cast" % election_id,
            params={"encrypted_vote": encrypted_vote},
        )
        self.assertRedirects(
            response,
            "%s/helios/elections/%s/cast_confirm"
            % (settings.SECURE_URL_HOST, election_id),
        )

        cast_confirm_page = response.follow()

        if need_login:
            if check_user_logged_in:
                self.assertContains(cast_confirm_page, "You are logged in as")
                self.assertContains(
                    cast_confirm_page, "requires election-specific credentials"
                )

            # set the form
            login_form = cast_confirm_page.form
            login_form["voter_id"] = username
            login_form["password"] = password

            response = login_form.submit()
        else:
            # here we should be at the cast-confirm page and logged in
            self.assertContains(cast_confirm_page, "CAST this ballot")

            # confirm the vote, now with the actual form
            cast_form = cast_confirm_page.form

            if "status_update" in cast_form.fields.keys():
                cast_form["status_update"] = False
            response = cast_form.submit()

        self.assertRedirects(
            response,
            "%s/helios/elections/%s/cast_done" % (
                settings.URL_HOST, election_id),
        )

        # at this point an email should have gone out to the user
        # at position num_messages after, since that was the len() before we cast this ballot
        email_message = mail.outbox[len(mail.outbox) - 1]
        url = re.search("https?://[^/]+(/[^ \n]*)",
                        email_message.body).group(1)

        # check that we can get at that URL
        if not need_login:
            # confusing piece: if need_login is True, that means it was a public election
            # that required login before casting a ballot.
            # so if need_login is False, it was a private election, and we do need to re-login here
            # we need to re-login if it's a private election, because all data, including ballots
            # is otherwise private
            login_page = self.app.get(
                "/helios/elections/%s/password_voter_login" % election_id
            )

            # if we redirected, that's because we can see the page, I think
            if login_page.status_int != 302:
                login_form = login_page.form

                # try with extra spaces
                login_form["voter_id"] = "  " + username + "   "
                login_form["password"] = "  " + password + "      "
                login_form.submit()

        response = self.app.get(url, auto_follow=True)
        self.assertContains(response, ballot.hash)
        self.assertContains(response, html_escape(encrypted_vote))

        # if we request the redirect to cast_done, the voter should be logged out, but not the user
        response = self.app.get("/helios/elections/%s/cast_done" % election_id)

        # FIXME: how to check this? We can't do it by checking session that we're doign webtes
        # assert not self.client.session.has_key('CURRENT_VOTER')

    def _do_tally(self, election_id):
        # log back in as administrator
        self.setup_login()

        # encrypted tally
        response = self.client.post(
            "/helios/elections/%s/compute_tally" % election_id,
            {"csrf_token": self.client.session["csrf_token"]},
        )
        self.assertRedirects(
            response, "/helios/elections/%s/view" % election_id)

        # should trigger helios decryption automatically
        self.assertNotEquals(
            models.Election.objects.get(uuid=election_id)
            .get_helios_trustee()
            .decryption_proofs,
            None,
        )

        # combine decryptions
        response = self.client.post(
            "/helios/elections/%s/combine_decryptions" % election_id,
            {"csrf_token": self.client.session["csrf_token"], },
        )

        # after tallying, we now go back to election_view
        self.assertRedirects(
            response, "/helios/elections/%s/view" % election_id)

        # check that we can't get the tally yet
        response = self.client.get("/helios/elections/%s/result" % election_id)
        self.assertStatusCode(response, 403)

        # release
        response = self.client.post(
            "/helios/elections/%s/release_result" % election_id,
            {"csrf_token": self.client.session["csrf_token"], },
        )

        # check that tally matches
        response = self.client.get("/helios/elections/%s/result" % election_id)
        self.assertEquals(utils.from_json(response.content), [[0, 1]])

    # def test_do_complete_election(self):
    #     election_id, username, password = self._setup_complete_election()
    #
    #     # cast a ballot while not logged in
    #     self._cast_ballot(election_id, username, password, check_user_logged_in=False)
    #
    #     # cast a ballot while logged in as a user (not a voter)
    #     self.setup_login()
    #
    #     ## for now the above does not work, it's a testing problem
    #     ## where the cookie isn't properly set. We'll have to figure this out.
    #     ## FIXME FIXME FIXME
    #     #self._cast_ballot(election_id, username, password, check_user_logged_in=True)
    #     self._cast_ballot(election_id, username, password, check_user_logged_in=False)
    #     self.clear_login()
    #
    #     self._do_tally(election_id)
    #
    # def test_do_complete_election_private(self):
    #     # private election
    #     election_id, username, password = self._setup_complete_election({'private_p' : "True"})
    #
    #     # get the password_voter_login_form via the front page
    #     # (which will test that redirects are doing the right thing)
    #     response = self.app.get("/helios/elections/%s/view" % election_id)
    #
    #     # ensure it redirects
    #     self.assertRedirects(response, "/helios/elections/%s/password_voter_login?%s" % (election_id, urllib.urlencode({"return_url": "/helios/elections/%s/view" % election_id})))
    #
    #     login_form = response.follow().form
    #
    #     login_form['voter_id'] = username
    #     login_form['password'] = password
    #
    #     response = login_form.submit()
    #     self.assertRedirects(response, "/helios/elections/%s/view" % election_id)
    #
    #     self._cast_ballot(election_id, username, password, need_login = False)
    #     self._do_tally(election_id)
    #
    # def test_election_voters_eligibility(self):
    #     # create the election
    #     self.setup_login(from_scratch=True)
    #     response = self.client.post("/helios/elections/new", {
    #             "short_name" : "test-eligibility",
    #             "name" : "Test Eligibility",
    #             "description" : "An election test for voter eligibility",
    #             "election_type" : "election",
    #             "use_voter_aliases": "0",
    #             "use_advanced_audit_features": "1",
    #             "private_p" : "False",
    #             'csrf_token': self.client.session['csrf_token']})
    #
    #     election_id = re.match("(.*)/elections/(.*)/view", str(response['Location']))
    #     self.assertIsNotNone(election_id, "Election id not found in redirect: %s" % str(response['Location']))
    #     election_id = election_id.group(2)
    #
    #     # update eligiblity
    #     response = self.client.post("/helios/elections/%s/voters/eligibility" % election_id, {
    #             "csrf_token" : self.client.session['csrf_token'],
    #             "eligibility": "openreg"})
    #
    #     self.clear_login()
    #     response = self.client.get("/helios/elections/%s/voters/list" % election_id)
    #     self.assertContains(response, "Anyone can vote")
    #
    #     self.setup_login()
    #     response = self.client.post("/helios/elections/%s/voters/eligibility" % election_id, {
    #             "csrf_token" : self.client.session['csrf_token'],
    #             "eligibility": "closedreg"})
    #
    #     self.clear_login()
    #     response = self.client.get("/helios/elections/%s/voters/list" % election_id)
    #     self.assertContains(response, "Only the voters listed here")
    #
    # def test_do_complete_election_with_trustees(self):
    #     """
    #     FIXME: do the this test
    #     """
    #     pass


class UtilityTests(TestCase):

    def test_qr_code_creation_base64(self):

        data_to_encode = "testtest"
        encoded_qr_image = (
            b"iVBORw0KGgoAAAANSUhEUgAAASIAAAEiAQAAAAB1xeIbAAABgElEQ"
            b"VR4nO2aMW6EMBRE3w+WUoK0BzI3i3IzfJQ9QCTojSaFjcNmi6QhEL"
            b"ALEPAkRmY0/nww8fMIL7+AoFKVqlSlKnV0yvJwWA9YPy1n+l11XYL"
            b"ykqQRCN1sGmgkSXqk/l7XJaipeHxazG/m9td1KcqPzXPZeQBdJ6Tc"
            b"t2OFDtv0jpVaxjL3rYAJzI+3aABr9x9V/f+m8tyH5PWmnJ8fzH9U9"
            b"f+bSnP/5XFBRI+uP676M1Bm3bqwsZ7ZCLW+35YilfF+bIRXREMr4c"
            b"f1VQ1HVX8GSgOzweTA3x3QKj2KnXWdm0opY9BEcsrnZVbQ1Pfa7an"
            b"k+xLwejcHoQPrd9V1bionehkpadJmzE2dmvfbUCVzAGiiQveBmG4y"
            b"mE176boQVfqY9nZ/FaGDtODurOvUVKkxKW20vMJqaGOtMbeknnppe"
            b"d9EA4f5YR9dl6SCOaCNQCtpOIquE1LPfUzNhh9mR7L8TrquQLH+NM"
            b"jSWNDI0l2oeb8ZZfXfqEpVqlKVugT1CeH0vMN7sIm9AAAAAElFTkS"
            b"uQmCC"
        )

        encoded_data = utils.create_qr_code_in_base64(data_to_encode)

        self.assertEquals(encoded_data, encoded_qr_image)
