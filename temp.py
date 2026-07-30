from src.llm.batch_processor import BatchProcessor

bp = BatchProcessor()
re = bp.process_batch(["Họ chia_sẻ về quy_trình sản_xuất lúa , kinh_nghiệm thực_tế giúp bà_con tối_ưu_hoá quy_trình sản_xuất hiện có , hiểu rõ về giống lúa chất_lượng cao và kỹ_thuật gieo_trồng có lợi cho môi_trường ."])
print(re)