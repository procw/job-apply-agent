from utils.staffing_agencies import (
    company_is_staffing_agency,
    staffing_agency_exclusion,
    staffing_agency_reason,
)


def _profile(**prefs):
    return {
        "preferences": {
            "exclude_staffing_agencies": prefs.pop("exclude_staffing_agencies", True),
            **prefs,
        },
        "languages": ["english"],
    }


def test_known_agency_by_company():
    assert staffing_agency_reason("TEKsystems", "") is not None
    assert staffing_agency_reason("Insight Global", "") is not None
    assert staffing_agency_reason("Acme Software Inc", "") is None


def test_company_name_pattern():
    assert staffing_agency_reason("BrightPath Staffing LLC", "") is not None


def test_exclusion_disabled():
    job = {"company": "TEKsystems", "title": "Engineer", "description": ""}
    profile = _profile(exclude_staffing_agencies=False)
    assert staffing_agency_exclusion(job, profile) is None


def test_exclusion_rejects_agency():
    job = {"company": "Robert Half Technology", "title": "Engineer", "description": ""}
    profile = _profile(exclude_staffing_agencies=True)
    code, detail = staffing_agency_exclusion(job, profile)
    assert code == "staffing_agency"
    assert "robert half" in detail


def test_exclusion_off_by_default():
    job = {"company": "TEKsystems", "title": "Engineer", "description": ""}
    assert staffing_agency_exclusion(job, {"preferences": {}, "languages": ["english"]}) is None


def test_company_is_staffing_agency():
    assert company_is_staffing_agency("Insight Global")
    assert not company_is_staffing_agency("1Password")


def test_allowlist():
    job = {"company": "TEKsystems", "title": "Engineer", "description": ""}
    profile = _profile(staffing_agency_allowlist=["TEKsystems"])
    assert staffing_agency_exclusion(job, profile) is None


def test_description_on_behalf_of_client():
    job = {
        "company": "Confidential",
        "title": "Software Engineer",
        "description": "We are hiring on behalf of our client in fintech.",
    }
    assert staffing_agency_exclusion(job, _profile()) is not None
