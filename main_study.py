import os
import struct

# 섹션의 시작과 끝을 나타내는 바이트 시퀀스
psa = b"\x50\x53\x61\x10\x64\x00\x00\x00"
endpsa = b"\x00\x00\x50\x45"

# NCP2 파일을 처리하는 클래스
class ncp2():
    def __init__(self):
        # 파일 내 위치를 저장하는 변수 (포인터 역할)
        self.pos = 0
        # 파일 데이터를 바이트 형태로 저장하는 변수
        self.data = b""
    
    # 파일을 열고 데이터를 읽어오는 함수
    def open(self, filename):
        f = open(filename, "rb")  # 바이너리 읽기 모드로 파일 열기
        self.pos = 0  # 파일 포인터 초기화
        self.data = f.read()  # 파일의 모든 데이터를 읽어서 self.data에 저장
        
    # 4바이트의 리틀 엔디언 값을 읽어오는 함수
    def _read_uint_le(self):
        value = struct.unpack("<I", self.data[self.pos:self.pos+4])[0]  # 4바이트를 리틀 엔디언으로 해석
        self.pos += 4  # 읽은 후 포인터를 4바이트 앞으로 이동
        return value
    
    # 32바이트의 헤더 데이터를 읽는 함수
    def _read_header(self):
        value = self.data[self.pos:self.pos+32]  # 현재 위치에서 32바이트 읽기
        self.pos += 32  # 포인터를 32바이트 앞으로 이동
        return value
    
    # 섹션의 시작을 확인하는 함수
    def _check_start_section(self):
        if self.data[self.pos:self.pos+8] == psa:  # 시작 바이트가 psa와 일치하는지 확인
            self.pos += 8  # 일치하면 포인터를 8바이트 앞으로 이동
            return True
        return False
    
    # 섹션의 끝을 확인하는 함수
    def _check_end_section(self):
        if self.data[self.pos:self.pos+4] == endpsa:  # 끝 바이트가 endpsa와 일치하는지 확인
            self.pos += 4  # 일치하면 포인터를 4바이트 앞으로 이동
            return True
        return False
    
    # 섹션을 읽어오는 함수 (이름, 길이, 데이터를 반환)
    def _read_section(self):
        sectionName = self.data[self.pos:self.pos+4]  # 섹션 이름 읽기 (4바이트)
        self.pos += 4
        
        sectionLength = self._read_uint_le()  # 섹션 길이 읽기
        
        sectionData = self.data[self.pos:self.pos+sectionLength]  # 섹션 데이터 읽기
        self.pos += sectionLength  # 포인터를 섹션 길이만큼 이동
        
        if not self._check_end_section():  # 섹션 끝을 확인
            raise Exception("Invalid Format")  # 끝 바이트가 일치하지 않으면 예외 발생
        
        return sectionName, sectionLength, sectionData  # 섹션 이름, 길이, 데이터 반환
    
    # 파일 테이블 섹션을 파싱하여 파일 목록을 생성하는 함수
    def _parse_file_table(self, data):
        file_table = []  # 파일 테이블 목록
        
        ppos = 0  # 파일 테이블 내 포인터
        
        while(ppos < len(data)):  # 파일 테이블 끝까지 반복
            name = data[ppos:ppos+44]  # 44바이트의 파일 이름 읽기
            ppos += 44
            
            start = struct.unpack("<I", data[ppos:ppos+4])[0]  # 파일의 시작 위치 읽기
            ppos += 8  # 파일 시작 위치 다음 4바이트는 사용되지 않음
            
            length = struct.unpack("<I", data[ppos:ppos+4])[0]  # 파일 길이 읽기
            ppos += 12  # 파일 길이 다음 8바이트는 사용되지 않음
            
            # 파일 이름을 디코딩하여 테이블에 추가 (널 문자 제거)
            file_table.append({"name": name.decode().replace("\x00", ""), "start": start, "length": length})
            
        return file_table  # 파싱된 파일 테이블 반환
    
    # 파일 테이블에 있는 파일들을 추출하는 함수
    def _extract_file_table(self, data, ft):
        for file in ft:  # 파일 테이블의 각 파일에 대해
            print(file)  # 파일 정보 출력
            ff = open(file["name"], "wb")  # 파일 이름으로 새 파일 열기 (바이너리 쓰기 모드)
            
            # 해당 파일 데이터를 원본 데이터에서 추출하여 쓰기
            ff.write(data[file["start"]:file["start"]+file["length"]])
            ff.close()  # 파일 닫기
            
    # NCP2 파일을 추출하는 메인 함수
    def extract(self):
        header = self._read_header()  # 파일 헤더 읽기
        if header[0:4] != b"NPQF":  # 헤더의 시작이 "NPQF"가 아닌 경우
            raise Exception("Invalid Header")  # 예외 발생
        
        # 데이터의 끝까지 반복하며 섹션을 처리
        while(self.pos < len(self.data)):
            if(self._check_start_section()):  # 시작 섹션이 맞는지 확인
                sectionName, sectionLength, sectionData = self._read_section()  # 섹션 읽기
                print(sectionName)  # 섹션 이름 출력
                if sectionName == b"INFO":  # INFO 섹션일 경우
                    print(sectionData)  # 섹션 데이터 출력

                # FTBL 섹션 (파일 테이블)인 경우 파일 테이블 파싱
                if sectionName == b"FTBL":
                    ft = self._parse_file_table(sectionData)
                
                # DATA 섹션인 경우 파일 테이블 기반으로 파일을 추출
                if sectionName == b"DATA":
                    self._extract_file_table(sectionData, ft)

# NCP2 파일을 열고 추출하는 작업 수행
n = ncp2()
n.open("CCE.ncp2")  # "CCE.ncp2" 파일 열기
n.extract()  # 파일에서 데이터를 추출
