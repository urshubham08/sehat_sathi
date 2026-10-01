from sqlalchemy import text
from src.database.database import engine
from src.security import hash_password

# Development/demo seed only.
# All 60 demo doctor accounts use the same temporary password:
# Doctor@123
#
# Change these credentials before any real deployment.

DOCTORS = [('Dr. Aarav Sharma', 'General Medicine', 'MBBS, MD (Medicine)', 12, 600), ('Dr. Ananya Verma', 'Cardiology', 'MBBS, MD, DM (Cardiology)', 15, 1200), ('Dr. Rohan Mehta', 'Dermatology', 'MBBS, MD (Dermatology)', 10, 800), ('Dr. Priya Singh', 'Pediatrics', 'MBBS, MD (Pediatrics)', 11, 700), ('Dr. Arjun Gupta', 'Orthopedics', 'MBBS, MS (Orthopedics)', 14, 900), ('Dr. Kavya Joshi', 'Gynecology', 'MBBS, MS (OBGYN)', 13, 900), ('Dr. Vivek Jain', 'Neurology', 'MBBS, MD, DM (Neurology)', 16, 1300), ('Dr. Meera Kapoor', 'Ophthalmology', 'MBBS, MS (Ophthalmology)', 9, 750), ('Dr. Aditya Bansal', 'ENT', 'MBBS, MS (ENT)', 8, 700), ('Dr. Neha Agarwal', 'Psychiatry', 'MBBS, MD (Psychiatry)', 10, 850), ('Dr. Kunal Malhotra', 'Gastroenterology', 'MBBS, MD, DM (Gastroenterology)', 17, 1400), ('Dr. Ishita Sethi', 'Endocrinology', 'MBBS, MD, DM (Endocrinology)', 12, 1200), ('Dr. Manav Choudhary', 'Pulmonology', 'MBBS, MD, DNB (Pulmonology)', 14, 1100), ('Dr. Riya Mishra', 'Nephrology', 'MBBS, MD, DM (Nephrology)', 13, 1200), ('Dr. Siddharth Rao', 'Urology', 'MBBS, MS, MCh (Urology)', 18, 1400), ('Dr. Nisha Arora', 'Dental', 'BDS, MDS', 9, 600), ('Dr. Harsh Vardhan', 'General Surgery', 'MBBS, MS (General Surgery)', 15, 1000), ('Dr. Simran Kaur', 'Nutrition & Dietetics', 'MSc (Nutrition), RD', 7, 500), ('Dr. Yash Patel', 'Physiotherapy', 'BPT, MPT', 8, 500), ('Dr. Tanvi Saxena', 'Radiology', 'MBBS, MD (Radiology)', 11, 1000), ('Dr. Rajat Khanna', 'Cardiology', 'MBBS, MD, DM (Cardiology)', 19, 1500), ('Dr. Pooja Nair', 'Pediatrics', 'MBBS, MD (Pediatrics)', 8, 700), ('Dr. Mohit Tiwari', 'Orthopedics', 'MBBS, MS (Orthopedics)', 12, 900), ('Dr. Sneha Iyer', 'Dermatology', 'MBBS, MD (Dermatology)', 9, 800), ('Dr. Devansh Kulkarni', 'General Medicine', 'MBBS, MD (Medicine)', 10, 600), ('Dr. Aditi Deshmukh', 'Gynecology', 'MBBS, MS (OBGYN)', 14, 950), ('Dr. Nitin Yadav', 'Neurology', 'MBBS, MD, DM (Neurology)', 11, 1250), ('Dr. Shreya Menon', 'Ophthalmology', 'MBBS, MS (Ophthalmology)', 10, 750), ('Dr. Abhishek Roy', 'ENT', 'MBBS, MS (ENT)', 13, 750), ('Dr. Sakshi Bhatt', 'Psychiatry', 'MBBS, MD (Psychiatry)', 8, 800), ('Dr. Varun Oberoi', 'Gastroenterology', 'MBBS, MD, DM (Gastroenterology)', 15, 1350), ('Dr. Manya Goel', 'Endocrinology', 'MBBS, MD, DM (Endocrinology)', 9, 1150), ('Dr. Sameer Khan', 'Pulmonology', 'MBBS, MD (Pulmonology)', 12, 1050), ('Dr. Alisha Thomas', 'Nephrology', 'MBBS, MD, DM (Nephrology)', 10, 1150), ('Dr. Pranav Shetty', 'Urology', 'MBBS, MS, MCh (Urology)', 14, 1350), ('Dr. Esha Bhatia', 'Dental', 'BDS, MDS', 6, 550), ('Dr. Vikram Rathore', 'General Surgery', 'MBBS, MS (General Surgery)', 17, 1050), ('Dr. Nandini Rao', 'Nutrition & Dietetics', 'MSc (Nutrition), RD', 6, 500), ('Dr. Omkar Desai', 'Physiotherapy', 'BPT, MPT', 9, 550), ('Dr. Aniket Soni', 'Radiology', 'MBBS, MD (Radiology)', 13, 1050), ('Dr. Lavanya Reddy', 'General Medicine', 'MBBS, MD (Medicine)', 7, 600), ('Dr. Rahul Srivastava', 'Cardiology', 'MBBS, MD, DM (Cardiology)', 16, 1250), ('Dr. Divya Chawla', 'Dermatology', 'MBBS, MD (Dermatology)', 11, 800), ('Dr. Ayush Tripathi', 'Pediatrics', 'MBBS, MD (Pediatrics)', 9, 700), ('Dr. Komal Sharma', 'Orthopedics', 'MBBS, MS (Orthopedics)', 10, 850), ('Dr. Saurabh Saxena', 'Gynecology', 'MBBS, MS (OBGYN)', 15, 950), ('Dr. Ritu Mahajan', 'Neurology', 'MBBS, MD, DM (Neurology)', 14, 1300), ('Dr. Tarun Bedi', 'Ophthalmology', 'MBBS, MS (Ophthalmology)', 12, 750), ('Dr. Monica Fernandes', 'ENT', 'MBBS, MS (ENT)', 9, 700), ('Dr. Akash Purohit', 'Psychiatry', 'MBBS, MD (Psychiatry)', 13, 850), ('Dr. Shalini Ghosh', 'Gastroenterology', 'MBBS, MD, DM (Gastroenterology)', 11, 1300), ('Dr. Chirag Bhardwaj', 'Endocrinology', 'MBBS, MD, DM (Endocrinology)', 10, 1150), ('Dr. Pallavi Naidu', 'Pulmonology', 'MBBS, MD (Pulmonology)', 8, 1000), ('Dr. Nikhil Bhat', 'Nephrology', 'MBBS, MD, DM (Nephrology)', 12, 1150), ('Dr. Ayesha Mirza', 'Urology', 'MBBS, MS, MCh (Urology)', 16, 1400), ('Dr. Manisha Sood', 'Dental', 'BDS, MDS', 10, 600), ('Dr. Raghav Pratap', 'General Surgery', 'MBBS, MS (General Surgery)', 12, 1000), ('Dr. Bhavna Dutta', 'Nutrition & Dietetics', 'MSc (Nutrition), RD', 8, 500), ('Dr. Farhan Ali', 'Physiotherapy', 'BPT, MPT', 7, 500), ('Dr. Jyoti Mehra', 'Radiology', 'MBBS, MD (Radiology)', 14, 1000)]
DEMO_PASSWORD = "Doctor@123"


def ensure_user_id_column(connection):
    exists = connection.execute(text("""
        SELECT COUNT(*)
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'doctors'
          AND COLUMN_NAME = 'user_id'
    """)).scalar()

    if not exists:
        connection.execute(
            text("ALTER TABLE doctors ADD COLUMN user_id INT NULL UNIQUE")
        )


def seed():
    password_hash = hash_password(DEMO_PASSWORD)

    with engine.begin() as connection:
        ensure_user_id_column(connection)

        for index, (name, specialty, qualification, experience, fee) in enumerate(DOCTORS, 1):
            email = f"doctor.demo{index:02d}@sanjeevani.local"
            mobile = f"900000{1000 + index:04d}"

            # Create the doctor profile if it does not already exist.
            existing_doctor = connection.execute(
                text("SELECT id FROM doctors WHERE email = :email LIMIT 1"),
                {"email": email},
            ).scalar()

            if existing_doctor is None:
                connection.execute(
                    text("""
                        INSERT INTO doctors
                        (user_id, name, specialty, qualification,
                         experience_years, consultation_fee,
                         availability_status, phone, email)
                        VALUES
                        (NULL, :name, :specialty, :qualification,
                         :experience_years, :consultation_fee,
                         'active', :phone, :email)
                    """),
                    {
                        "name": name,
                        "specialty": specialty,
                        "qualification": qualification,
                        "experience_years": experience,
                        "consultation_fee": fee,
                        "phone": mobile,
                        "email": email,
                    },
                )

            # Create the login account if it does not already exist.
            user_id = connection.execute(
                text("SELECT id FROM users WHERE email = :email LIMIT 1"),
                {"email": email},
            ).scalar()

            if user_id is None:
                connection.execute(
                    text("""
                        INSERT INTO users
                        (name, email, mobile, password_hash, role, is_active)
                        VALUES
                        (:name, :email, :mobile, :password_hash, 'doctor', TRUE)
                    """),
                    {
                        "name": name,
                        "email": email,
                        "mobile": mobile,
                        "password_hash": password_hash,
                    },
                )
                user_id = connection.execute(
                    text("SELECT id FROM users WHERE email = :email LIMIT 1"),
                    {"email": email},
                ).scalar()

            # Link doctor profile to its login user.
            connection.execute(
                text("""
                    UPDATE doctors
                    SET user_id = :user_id
                    WHERE email = :email
                """),
                {"user_id": user_id, "email": email},
            )

    print("SUCCESS: 60 demo doctors + 60 doctor login accounts are ready.")
    print("Demo login password for all doctors: Doctor@123")
    print("Example login: doctor.demo01@sanjeevani.local")
    print("Change demo passwords before production use.")


if __name__ == "__main__":
    seed()
