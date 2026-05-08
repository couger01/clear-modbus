from modbus.constants import MODBUS_TCP_PROTOCOL_ID
import pytest

from modbus.protocol.mbap import MBAPHeader, ModbusTCPFrame


def test_mbap_header_encodes_expected_bytes() -> None:
    header = MBAPHeader(transaction_id=1, protocol_id=MODBUS_TCP_PROTOCOL_ID, length=6, unit_id=1)
    assert header.encode() == bytes.fromhex("00 01 00 00 00 06 01")


def test_mbap_header_decodes_expected_fields() -> None:
    header = MBAPHeader.decode(bytes.fromhex("00 01 00 00 00 06 01"))
    assert header.transaction_id == 1
    assert header.protocol_id == MODBUS_TCP_PROTOCOL_ID
    assert header.length == 6
    assert header.unit_id == 1


def test_mbap_header_rejects_invalid_length() -> None:
    with pytest.raises(ValueError):
        MBAPHeader.decode(bytes.fromhex("00 00 00 00 00 00"))
    with pytest.raises(ValueError):
        MBAPHeader.decode(bytes.fromhex("00 00 00 00 00 00 00 00"))


def test_modbus_tcp_frame_encodes_header_plus_pdu() -> None:
    frame = ModbusTCPFrame(transaction_id=1, unit_id=1, pdu=bytes.fromhex("03 00 00 00 02"))

    assert frame.encode() == bytes.fromhex("00 01 00 00 00 06 01 03 00 00 00 02")


def test_modbus_tcp_frame_decodes_header_and_pdu() -> None:
    frame = ModbusTCPFrame.decode(bytes.fromhex("00 01 00 00 00 06 01 03 00 00 00 02"))
    assert frame.transaction_id == 1
    assert frame.unit_id == 1
    assert frame.protocol_id == MODBUS_TCP_PROTOCOL_ID
    assert frame.pdu == bytes.fromhex("03 00 00 00 02")


def test_modbus_tcp_frame_rejects_nonzero_protocol_id() -> None:
    with pytest.raises(ValueError):
        ModbusTCPFrame.decode(bytes.fromhex("00 01 00 01 00 06 01 03 00 00 00 02"))


def test_modbus_tcp_frame_rejects_length_mismatch() -> None:
    with pytest.raises(ValueError):
        ModbusTCPFrame.decode(bytes.fromhex("00 01 00 00 00 07 01 03 00 00 00 02"))
