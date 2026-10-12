"""Test consent forms for development and testing only.

These are placeholders so the consent flow can be built and tried. They are flagged
is_test_form, refused in production, and say on their face that they are not for real data.
Real forms come from the professor and ethics committee (Q-L3) and are never written here.
"""

import hashlib
from dataclasses import dataclass

FORM_CODE = "LKD-TEST-CONSENT"
VERSION = "0.1-test"


@dataclass(frozen=True)
class DevForm:
    language: str
    body_markdown: str

    @property
    def text_sha256(self) -> str:
        return hashlib.sha256(self.body_markdown.encode("utf-8")).hexdigest()


DEV_FORMS = (
    DevForm(
        language="hi",
        body_markdown=(
            "# परीक्षण सहमति पत्र\n\n"
            "**यह केवल परीक्षण के लिए है। इससे किसी की असली रिकॉर्डिंग न लें।**\n\n"
            "लोकधारा मुंडारी भाषा को सहेजने की एक परियोजना है। असली सहमति पत्र में बताया "
            "जाएगा कि परियोजना कौन चलाता है, रिकॉर्डिंग कहाँ रखी जाती है, उसे कौन सुन सकता "
            "है, वह कितने समय तक रखी जाती है, और आप अपनी सहमति कैसे वापस ले सकते हैं। "
            "वह पत्र नैतिकता समिति की स्वीकृति के बाद जोड़ा जाएगा।\n"
        ),
    ),
    DevForm(
        language="en",
        body_markdown=(
            "# Test consent form\n\n"
            "**For testing only. Do not use it to record anyone for real.**\n\n"
            "Lokdhara is a project to preserve the Mundari language. The real consent form "
            "will explain who runs the project, where recordings are kept, who can hear them, "
            "how long they are kept, and how to withdraw consent. It will be added after "
            "ethics committee approval.\n"
        ),
    ),
)
