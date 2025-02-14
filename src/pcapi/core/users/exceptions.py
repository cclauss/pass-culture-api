class CredentialsException(Exception):
    pass


class InvalidIdentifier(CredentialsException):
    pass


class UnvalidatedAccount(CredentialsException):
    pass


class UserAlreadyExistsException(Exception):
    pass


class NotEligible(Exception):
    pass


class UnderAgeUserException(Exception):
    pass


class EmailNotSent(Exception):
    pass


class PhoneVerificationException(Exception):
    pass


class PhoneVerificationCodeSendingException(PhoneVerificationException):
    pass


class SMSSendingLimitReached(PhoneVerificationException):
    pass


class PhoneValidationAttemptsLimitReached(PhoneVerificationException):
    pass


class PhoneAlreadyExists(PhoneVerificationException):
    pass


class UnvalidatedEmail(PhoneVerificationException):
    pass


class UserPhoneNumberAlreadyValidated(PhoneVerificationException):
    pass


class UserWithoutPhoneNumberException(PhoneVerificationException):
    pass


class UserAlreadyBeneficiary(PhoneVerificationException):
    pass


class NotValidCode(PhoneVerificationException):
    pass


class ExpiredCode(NotValidCode):
    pass


class IdCheckTokenLimitReached(Exception):
    pass


class IdCheckAlreadyCompleted(Exception):
    pass


class BeneficiaryImportMissingException(Exception):
    pass


class InvalidPhoneNumber(PhoneVerificationException):
    pass


class UserDoesNotExist(Exception):
    pass


class IdentityDocumentUploadException(Exception):
    pass


class CloudTaskCreationException(Exception):
    pass


class MissingEmailInMetadataException(Exception):
    pass


class IdentityDocumentVerificationException(Exception):
    pass
