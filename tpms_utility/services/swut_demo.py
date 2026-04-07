import logging
from swut.library.diagnostic_library import DiagnosticLibrary


logger = logging.getLogger(__name__)


def check_hpa_working(diag_obj: DiagnosticLibrary):
    logger.info(f"<<<<<<<<<<<<< Check that HPA is working <<<<<<")
    diag_obj.send_request(
        "22F186",
        "to",
        "HPA",
        "response should match 62 F1 86 01",
    )


def check_tca_working(diag_obj: DiagnosticLibrary):
    logger.info(f"<<<<<<<<<<<<< Check that TCA is working <<<<<<")
    diag_obj.send_request(
        "22F186",
        "to",
        "TCA",
        "response should match 62 F1 86 01",
        # "continue on fail",
    )


def write_wheel_unit_ids(diag_obj: DiagnosticLibrary):
    logger.info(f"<<<<<<<<<<< Overwriting WU Ids <<<<")

    # Equivalent to 1D12 2E20EB20000001200000022000000320000004
    diag_obj.send_request(
        "2E 20 EB 20000001200000022000000320000004",
        "to",
        "HPA",
        "response should match 6E 20 EB",
        timeout=10,
    )


def check_one_wheel_unit_id(diag_obj: DiagnosticLibrary, wheel_unit_id):
    logger.info(f"<<<<<<<<<<< checking that wheel_unit_id exists in memory <<<<")
    diag_obj.send_request(
        "22 20 EB",
        "to",
        "HPA",
        "response should contain " + wheel_unit_id,
        # "continue on fail",
    )


def start_dtpms_debug(diag_obj: DiagnosticLibrary):
    logger.info(f"<<<<<<<<<<< starting routine dtpms debug <<<<")
    diag_obj.send_request(
        "31 01 DF 04",
        "to",
        "HPA",
        "response should contain 71 01 DF 04 30",
    )


def stop_dtpms_debug(diag_obj: DiagnosticLibrary):
    logger.info(f"<<<<<<<<<<< Stopping routine dtpms debug <<<<")
    diag_obj.send_request(
        "31 02 DF 04",
        "to",
        "HPA",
    )


def unlock_diag_firewall_hpa(diag_obj: DiagnosticLibrary):
    diag_obj.unlock_security_area(
        "17",
        "on",
        "HPA",
        pin="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
    )


def set_extended_session_hpa(diag_obj: DiagnosticLibrary):
    diag_obj.send_request(
        "1003",
        "to",
        "HPA",
        "response should contain 32 01 F4",
    )


def unlock_security_area_05_hpa(diag_obj: DiagnosticLibrary):
    diag_obj.unlock_security_area(
        "05",
        "on",
        "HPA",
        pin="FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF",
    )


def start_routine_set_tpms_fault(diag_obj: DiagnosticLibrary, payload):
    diag_obj.send_request(
        "31 01 DF 06 " + payload,
        "to",
        "HPA",
    )


def start_routine_set_low_pressure_warning_front_left(
    diag_obj: DiagnosticLibrary, active: bool
):
    if active:
        diag_obj.send_request(
            "31 01 DF 0A 01",
            "to",
            "HPA",
        )
    else:
        diag_obj.send_request(
            "31 01 DF 0A 00",
            "to",
            "HPA",
        )


def start_routine_set_severe_low_pressure_warning_front_left(
    diag_obj: DiagnosticLibrary, active: bool
):
    if active:
        diag_obj.send_request(
            "31 01 DF 0E 01",
            "to",
            "HPA",
        )
    else:
        diag_obj.send_request(
            "31 01 DF 0E 00",
            "to",
            "HPA",
        )

def itpms_did_read_sw_version(diag_obj: DiagnosticLibrary = DiagnosticLibrary()):
    logger.info(f"<<<<<<<<<<< reading software version from iTPMS <<<<")
    ret = diag_obj.send_request(
        "22 EF 1B",
        "to",
        "ZCLA",
    )
    return ret.response[0].response