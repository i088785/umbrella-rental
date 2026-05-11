import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import os

st.set_page_config(
    page_title="우산대여 관리",
    page_icon="☂️",
    layout="wide"
)

RENTAL_FILE = "rentals.csv"
RETURN_FILE = "return_logs.csv"
WARNING_FILE = "warning_logs.csv"

TOTAL_UMBRELLAS = 20
UMBRELLAS = [f"{i}번우산" for i in range(1, TOTAL_UMBRELLAS + 1)]


def normalize_umbrella_number(text):
    text = text.strip().replace(" ", "")
    if text.endswith("번"):
        text += "우산"
    return text


def calculate_due_date(rent_date):
    # 금요일 대여면 월요일 반납
    if rent_date.weekday() == 4:
        return rent_date + timedelta(days=3)
    return rent_date + timedelta(days=1)


def calculate_overdue_days(due_date):
    overdue_days = (date.today() - due_date).days
    return max(overdue_days, 0)


def load_data(filename):
    if os.path.exists(filename):
        df = pd.read_csv(filename, dtype={"학번": str, "전화번호": str})

        for column in ["대여일", "반납예정일", "반납처리일", "경고일"]:
            if column in df.columns:
                df[column] = pd.to_datetime(df[column]).dt.date

        return df.to_dict("records")

    return []


def save_data(filename, data):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False, encoding="utf-8-sig")


def parse_rental_text(text):
    parts = [part.strip() for part in text.split("/")]

    if len(parts) != 5:
        raise ValueError("형식이 틀렸습니다. 예: 학번/이름/전화번호/우산번호/대여날짜")

    student_id, name, phone, umbrella_number, rent_date_text = parts
    umbrella_number = normalize_umbrella_number(umbrella_number)

    rent_date = datetime.strptime(rent_date_text, "%Y.%m.%d").date()

    return {
        "학번": student_id,
        "이름": name,
        "전화번호": phone,
        "우산번호": umbrella_number,
        "대여일": rent_date,
        "반납예정일": calculate_due_date(rent_date),
        "상태": "대여중"
    }


def get_warning_count(student_id):
    count = 0
    for warning in st.session_state.warning_logs:
        if str(warning["학번"]) == str(student_id):
            count += 1
    return count


def add_warning(rental, overdue_days):
    warning = {
        "학번": rental["학번"],
        "이름": rental["이름"],
        "전화번호": rental["전화번호"],
        "우산번호": rental["우산번호"],
        "대여일": rental["대여일"],
        "반납예정일": rental["반납예정일"],
        "경고일": date.today(),
        "연체일수": overdue_days,
        "경고사유": "반납기한 미준수"
    }
    st.session_state.warning_logs.append(warning)
    save_data(WARNING_FILE, st.session_state.warning_logs)


def reset_edit_state():
    st.session_state.edit_index = None


if "rentals" not in st.session_state:
    st.session_state.rentals = load_data(RENTAL_FILE)

if "return_logs" not in st.session_state:
    st.session_state.return_logs = load_data(RETURN_FILE)

if "warning_logs" not in st.session_state:
    st.session_state.warning_logs = load_data(WARNING_FILE)

if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if not st.session_state.is_logged_in:
    st.title("☂️ 관리자 로그인")
    st.write("관리자 비밀번호를 입력하세요")

    password = st.text_input("비밀번호", type="password")

    if st.button("로그인", type="primary"):
        if password.lower() == "bloom":
            st.session_state.is_logged_in = True
            st.success("로그인되었습니다.")
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")

    st.stop()


st.title("☂️ 바이오신약융합학부 우산대여 관리")
st.caption("오픈채팅방 신청을 그대로 복사하면 자동으로 정리됩니다.")

st.divider()

st.subheader("1. 우산대여자 정보")

rental_text = st.text_input(
    "해당 신청 문구",
    placeholder="예: 학번/이름/전화번호/우산번호/대여날짜"
)

if st.button("대여자 정보 등록", type="primary"):
    try:
        new_rental = parse_rental_text(rental_text)

        warning_count = get_warning_count(new_rental["학번"])
        rented_umbrellas = [
            rental["우산번호"] for rental in st.session_state.rentals
        ]

        if warning_count >= 2:
            st.error(f"이용제한자입니다. {new_rental['이름']} 학생은 경고 {warning_count}회 누적으로 우산대여사업 이용이 제한됩니다.")

        elif new_rental["우산번호"] not in UMBRELLAS:
            st.error("등록되지 않은 우산 번호입니다.")

        elif new_rental["우산번호"] in rented_umbrellas:
            st.error(f"{new_rental['우산번호']}은/는 이미 대여중입니다.")

        else:
            st.session_state.rentals.append(new_rental)
            save_data(RENTAL_FILE, st.session_state.rentals)
            st.success("대여자 정보 등록 완료!")
            st.rerun()

    except Exception as e:
        st.error(str(e))

st.divider()

rented_umbrellas = [rental["우산번호"] for rental in st.session_state.rentals]
available_umbrellas = [
    umbrella for umbrella in UMBRELLAS if umbrella not in rented_umbrellas
]

overdue_list = []
for rental in st.session_state.rentals:
    overdue_days = calculate_overdue_days(rental["반납예정일"])
    if overdue_days > 0:
        item = rental.copy()
        item["연체일수"] = overdue_days
        overdue_list.append(item)

warning_summary = {}
for warning in st.session_state.warning_logs:
    student_id = str(warning["학번"])
    if student_id not in warning_summary:
        warning_summary[student_id] = {
            "학번": warning["학번"],
            "이름": warning["이름"],
            "전화번호": warning["전화번호"],
            "경고횟수": 0
        }
    warning_summary[student_id]["경고횟수"] += 1

warning_1_list = [item for item in warning_summary.values() if item["경고횟수"] == 1]
warning_2_list = [item for item in warning_summary.values() if item["경고횟수"] >= 2]

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("전체", f"{TOTAL_UMBRELLAS}개")
col2.metric("대여중", f"{len(rented_umbrellas)}개")
col3.metric("연체", f"{len(overdue_list)}명")
col4.metric("경고 1회", f"{len(warning_1_list)}명")
col5.metric("이용제한", f"{len(warning_2_list)}명")

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("2. 현재 대여중")

    if not st.session_state.rentals:
        st.info("현재 대여중인 우산이 없습니다.")

    else:
        for index, rental in enumerate(st.session_state.rentals):
            overdue_days = calculate_overdue_days(rental["반납예정일"])
            warning_count = get_warning_count(rental["학번"])

            with st.container(border=True):
                if st.session_state.edit_index == index:
                    st.write("### 대여 정보 수정")

                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:
                        new_student_id = st.text_input("학번", value=rental["학번"], key=f"edit_student_id_{index}")
                        new_name = st.text_input("이름", value=rental["이름"], key=f"edit_name_{index}")
                        new_phone = st.text_input("전화번호", value=rental["전화번호"], key=f"edit_phone_{index}")

                    with edit_col2:
                        new_umbrella_number = st.selectbox(
                            "우산번호",
                            UMBRELLAS,
                            index=UMBRELLAS.index(rental["우산번호"]) if rental["우산번호"] in UMBRELLAS else 0,
                            key=f"edit_umbrella_{index}"
                        )
                        new_rent_date = st.date_input("대여일", value=rental["대여일"], key=f"edit_rent_date_{index}")
                        new_due_date = st.date_input("반납예정일", value=rental["반납예정일"], key=f"edit_due_date_{index}")

                    save_col, cancel_col = st.columns([1, 5])

                    if save_col.button("수정저장", type="primary", key=f"save_edit_{index}"):
                        other_rented_umbrellas = [
                            item["우산번호"]
                            for i, item in enumerate(st.session_state.rentals)
                            if i != index
                        ]

                        if new_umbrella_number in other_rented_umbrellas:
                            st.error(f"{new_umbrella_number}은/는 이미 다른 학생이 대여중입니다.")
                        else:
                            st.session_state.rentals[index] = {
                                "학번": new_student_id,
                                "이름": new_name,
                                "전화번호": new_phone,
                                "우산번호": new_umbrella_number,
                                "대여일": new_rent_date,
                                "반납예정일": new_due_date,
                                "상태": "대여중"
                            }
                            save_data(RENTAL_FILE, st.session_state.rentals)
                            reset_edit_state()
                            st.success("수정되었습니다.")
                            st.rerun()

                    if cancel_col.button("수정취소", key=f"cancel_edit_{index}"):
                        reset_edit_state()
                        st.rerun()

                else:
                    if overdue_days > 0:
                        st.markdown(f"<span style='color:red; font-weight:700;'>{rental['이름']}</span> / {rental['학번']}", unsafe_allow_html=True)
                    else:
                        st.write(f"**{rental['이름']}** / {rental['학번']}")
                    st.write(f"전화번호: {rental['전화번호']}")
                    st.write(f"우산번호: {rental['우산번호']}")
                    st.write(f"대여일: {rental['대여일'].strftime('%Y.%m.%d')}")
                    st.write(f"반납예정일: {rental['반납예정일'].strftime('%Y.%m.%d')}")
                    st.write(f"현재 경고: {warning_count}회")

                    if overdue_days > 0:
                        st.warning(f"{overdue_days}일 연체 - 반납완료 처리 시 경고 1회가 부과됩니다.")

                    btn_col1, btn_col2 = st.columns([1, 1])

                    if btn_col1.button("수정", key=f"edit_{index}"):
                        st.session_state.edit_index = index
                        st.rerun()

                    if btn_col2.button("반납완료", key=f"return_{index}"):
                        returned = st.session_state.rentals.pop(index)
                        returned["반납처리일"] = date.today()

                        final_overdue_days = calculate_overdue_days(returned["반납예정일"])
                        if final_overdue_days > 0:
                            add_warning(returned, final_overdue_days)
                            returned["경고부과"] = "예"
                            returned["연체일수"] = final_overdue_days
                        else:
                            returned["경고부과"] = "아니오"
                            returned["연체일수"] = 0

                        st.session_state.return_logs.append(returned)

                        save_data(RENTAL_FILE, st.session_state.rentals)
                        save_data(RETURN_FILE, st.session_state.return_logs)

                        st.rerun()


with right:
    st.subheader("3. 우산 현황")

    st.write("**대여중인 우산**")
    if rented_umbrellas:
        st.write(", ".join(rented_umbrellas))
    else:
        st.write("없음")

    st.write("**대여 가능한 우산**")
    if available_umbrellas:
        st.write(", ".join(available_umbrellas))
    else:
        st.write("없음")


st.divider()

st.subheader("4. 연체자 명단")

if not overdue_list:
    st.success("현재 연체자가 없습니다.")
else:
    overdue_df = pd.DataFrame(overdue_list)
    overdue_df["대여일"] = overdue_df["대여일"].apply(lambda x: x.strftime("%Y.%m.%d"))
    overdue_df["반납예정일"] = overdue_df["반납예정일"].apply(lambda x: x.strftime("%Y.%m.%d"))

    st.dataframe(
        overdue_df[
            ["학번", "이름", "전화번호", "우산번호", "대여일", "반납예정일", "연체일수"]
        ],
        use_container_width=True,
        hide_index=True
    )

st.divider()

st.subheader("5. 경고 및 이용제한 명단")

warning_tab1, warning_tab2, warning_tab3 = st.tabs(["경고 1회", "경고 2회 이상 / 이용제한", "전체 경고 기록"])

with warning_tab1:
    if not warning_1_list:
        st.info("경고 1회 대상자가 없습니다.")
    else:
        st.dataframe(pd.DataFrame(warning_1_list), use_container_width=True, hide_index=True)

with warning_tab2:
    if not warning_2_list:
        st.success("현재 이용제한 대상자가 없습니다.")
    else:
        st.error("아래 학생은 경고 2회 이상으로 우산대여사업 이용이 제한됩니다.")
        st.dataframe(pd.DataFrame(warning_2_list), use_container_width=True, hide_index=True)

with warning_tab3:
    if not st.session_state.warning_logs:
        st.info("아직 경고 기록이 없습니다.")
    else:
        warning_df = pd.DataFrame(st.session_state.warning_logs)
        for column in ["대여일", "반납예정일", "경고일"]:
            warning_df[column] = warning_df[column].apply(lambda x: x.strftime("%Y.%m.%d"))
        st.dataframe(
            warning_df[["학번", "이름", "전화번호", "우산번호", "대여일", "반납예정일", "경고일", "연체일수", "경고사유"]],
            use_container_width=True,
            hide_index=True
        )

st.divider()

st.subheader("6. 반납 기록")

if not st.session_state.return_logs:
    st.info("아직 반납 기록이 없습니다.")
else:
    log_df = pd.DataFrame(st.session_state.return_logs)
    for column in ["대여일", "반납예정일", "반납처리일"]:
        log_df[column] = log_df[column].apply(lambda x: x.strftime("%Y.%m.%d"))

    if "경고부과" not in log_df.columns:
        log_df["경고부과"] = "아니오"
    if "연체일수" not in log_df.columns:
        log_df["연체일수"] = 0

    st.dataframe(
        log_df[
            ["학번", "이름", "전화번호", "우산번호", "대여일", "반납예정일", "반납처리일", "연체일수", "경고부과"]
        ],
        use_container_width=True,
        hide_index=True
    )
